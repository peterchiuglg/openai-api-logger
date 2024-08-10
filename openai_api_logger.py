import json
import os
import sqlite3
import threading
from time import time, strftime, gmtime
from typing import List, Tuple, Optional, Union

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai.types.embedding import Embedding
from tqdm import tqdm

# Load environment variables
load_dotenv()

API_KEY = os.getenv('OPENAI_API_KEY')
MODEL_CHAT_COMPLETION = os.getenv('MODEL_CHAT_COMPLETION')
MODEL_EMBEDDING = os.getenv('MODEL_EMBEDDING')
SQLITE_FILE = os.getenv('SQLITE_FILE')

print('chat completion model:', MODEL_CHAT_COMPLETION)
print('embedding model:', MODEL_EMBEDDING)
print('logging:', SQLITE_FILE)

client = OpenAI(api_key=API_KEY)

db_lock = threading.Lock()


def get_db_connection():
    connection = sqlite3.connect(SQLITE_FILE, check_same_thread=False)
    cursor = connection.cursor()
    return connection, cursor


def close_db_connection(connection):
    connection.close()


def list_tables():
    conn, cursor = get_db_connection()
    with db_lock:

        try:
            # Execute a query to retrieve all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")

            # Fetch all results from the executed query
            tables = cursor.fetchall()

            # Print the list of tables
            return [table[0] for table in tables]

        except sqlite3.Error as e:
            print(f"An error occurred: {e}")

    close_db_connection(conn)


# Rename 'logs' table to 'chat_completion_logs' if it exists
# rename_logs_table()

# Initialize SQLite database in the main thread
main_conn, main_cursor = get_db_connection()

# Create table for logging chat completions if it doesn't exist
with db_lock:
    main_cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_completion_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        input_messages TEXT,
        max_tokens INTEGER,
        temperature REAL,
        top_p REAL,
        frequency_penalty REAL,
        output_text TEXT,
        input_tokens INTEGER,
        output_tokens INTEGER,
        time_taken REAL
    )
    ''')

    # Create table for logging embeddings if it doesn't exist
    main_cursor.execute('''
    CREATE TABLE IF NOT EXISTS embedding_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        input_texts TEXT,
        model TEXT,
        tokens INTEGER,
        time_taken REAL
    )
    ''')

    main_conn.commit()
close_db_connection(main_conn)


def log_chat_completion(timestamp, input_messages, max_tokens, temperature, top_p, frequency_penalty, output_text,
                        input_tokens, output_tokens, time_taken):
    conn, cursor = get_db_connection()
    with db_lock:
        cursor.execute('''
        INSERT INTO chat_completion_logs (timestamp, input_messages, max_tokens, temperature, top_p, frequency_penalty, output_text, input_tokens, output_tokens, time_taken)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, input_messages, max_tokens, temperature, top_p, frequency_penalty, output_text, input_tokens,
              output_tokens, time_taken))
        conn.commit()
    close_db_connection(conn)


def log_embedding(timestamp, input_text, model, tokens, time_taken):
    conn, cursor = get_db_connection()
    with db_lock:
        cursor.execute('''
        INSERT INTO embedding_logs (timestamp, input_texts, model, tokens, time_taken)
        VALUES (?, ?, ?, ?,?)
        ''', (timestamp, input_text, model, tokens, time_taken))
        conn.commit()
    close_db_connection(conn)


def chat_completion(messages: List[dict], max_tokens: int, temperature: float, top_p: float, frequency_penalty: float,
                    model: str = MODEL_CHAT_COMPLETION, timeout: int = 60) -> Tuple[str, int, int, float]:
    t0 = time()
    response: ChatCompletion = client.chat.completions.create(model=model, temperature=temperature,
                                                              max_tokens=max_tokens, top_p=top_p,
                                                              frequency_penalty=frequency_penalty, messages=messages,
                                                              timeout=timeout)
    time_taken = time() - t0
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    generated_text = response.choices[0].message.content

    # Log input and output values along with timestamp
    timestamp = strftime('%Y-%m-%d %H:%M:%S', gmtime())
    log_chat_completion(timestamp, json.dumps(messages), max_tokens, temperature, top_p, frequency_penalty,
                        generated_text, input_tokens, output_tokens, time_taken)

    return generated_text, input_tokens, output_tokens, time_taken


def embed_one(text: str, model: str = MODEL_EMBEDDING, return_usage: bool = False) -> Union[
    List[float], Tuple[List[float], int]]:
    t0 = time()
    r: Embedding = client.embeddings.create(input=[text], model=model)
    time_taken = time() - t0

    timestamp = strftime('%Y-%m-%d %H:%M:%S', gmtime())
    log_embedding(timestamp, json.dumps([text]), model, r.usage.total_tokens, time_taken)

    if return_usage:
        return r.data[0].embedding, r.usage.total_tokens
    return r.data[0].embedding


def embed(texts: List[str], model: str = MODEL_EMBEDDING, batch: Optional[int] = None, return_usage: bool = False) -> \
    Union[List[List[float]], Tuple[List[List[float]], int]]:
    if batch is not None:
        if not isinstance(batch, int):
            raise TypeError("batch must be an integer")
        if batch <= 0:
            raise ValueError("batch must be a positive integer")
        if batch > len(texts):
            print(
                f"Warning: batch size ({batch}) is larger than the number of texts ({len(texts)}). Setting batch size to {len(texts)}.")
            batch = len(texts)
    else:
        batch = len(texts)

    res: List[List[float]] = []
    usages: List[int] = []
    it = range(0, len(texts), batch)
    if batch != len(texts):
        it = tqdm(it)
    for i in it:
        batch_texts = texts[i:i + batch]
        for text in batch_texts:
            if return_usage:
                embedding, usage = embed_one(text, model, return_usage=True)
                res.append(embedding)
                usages.append(usage)
            else:
                embedding = embed_one(text, model, return_usage=False)
                res.append(embedding)

    if return_usage:
        return res, sum(usages)
    return res


def dump_logs_to_jsonl(dir_path):
    for table_name in list_tables():
        jsonl_file_path = os.path.join(dir_path, f'{table_name}.jsonl')
        conn, cursor = get_db_connection()
        with db_lock:
            cursor.execute(f'SELECT * FROM {table_name}')
            rows = cursor.fetchall()
        close_db_connection(conn)

        if len(rows) == 0:
            continue

        # Get column names from the description property of the cursor
        column_names = [description[0] for description in cursor.description]

        # Write each row as a JSON object on a new line in the JSONL file
        with open(jsonl_file_path, 'w') as jsonl_file:
            for row in rows:
                log = dict(zip(column_names, row))
                jsonl_file.write(json.dumps(log) + '\n')

        print(f"{table_name} content dumped to {jsonl_file_path}")
