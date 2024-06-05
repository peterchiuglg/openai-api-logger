import json
import os
import sqlite3
import threading
from time import time, strftime, gmtime

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

api_key = os.getenv('API_KEY')
model = os.getenv('MODEL')
sqlite_file = os.getenv('SQLITE_FILE')

client = OpenAI(api_key=api_key)

db_lock = threading.Lock()


def get_db_connection():
    connection = sqlite3.connect(sqlite_file, check_same_thread=False)
    cursor = connection.cursor()
    return connection, cursor


def close_db_connection(connection):
    connection.close()


# Initialize SQLite database in the main thread
main_conn, main_cursor = get_db_connection()

# Create table for logging if it doesn't exist
with db_lock:
    main_cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
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
    main_conn.commit()
close_db_connection(main_conn)


def log_to_db(timestamp, input_messages, max_tokens, temperature, top_p, frequency_penalty, output_text, input_tokens,
              output_tokens, time_taken):
    conn, cursor = get_db_connection()
    with db_lock:
        cursor.execute('''
        INSERT INTO logs (timestamp, input_messages, max_tokens, temperature, top_p, frequency_penalty, output_text, input_tokens, output_tokens, time_taken)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, input_messages, max_tokens, temperature, top_p, frequency_penalty, output_text, input_tokens,
              output_tokens, time_taken))
        conn.commit()
    close_db_connection(conn)


def chat_completion(messages, max_tokens, temperature, top_p, frequency_penalty, model=model):
    t0 = time()
    response = client.chat.completions.create(model=model, temperature=temperature, max_tokens=max_tokens, top_p=top_p,
                                              frequency_penalty=frequency_penalty, messages=messages)
    time_taken = time() - t0
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    generated_text = response.choices[0].message.content

    # Log input and output values along with timestamp
    timestamp = strftime('%Y-%m-%d %H:%M:%S', gmtime())
    log_to_db(timestamp, json.dumps(messages), max_tokens, temperature, top_p, frequency_penalty, generated_text,
              input_tokens, output_tokens, time_taken)

    return generated_text, input_tokens, output_tokens, time_taken


def dump_logs_to_jsonl(jsonl_file_path):
    conn, cursor = get_db_connection()
    with db_lock:
        cursor.execute('SELECT * FROM logs')
        rows = cursor.fetchall()
    close_db_connection(conn)

    # Get column names from the description property of the cursor
    column_names = [description[0] for description in cursor.description]

    # Write each row as a JSON object on a new line in the JSONL file
    with open(jsonl_file_path, 'w') as jsonl_file:
        for row in rows:
            log = dict(zip(column_names, row))
            jsonl_file.write(json.dumps(log) + '\n')

    print(f"Database content dumped to {jsonl_file_path}")
