# Client-Side Logging for OpenAI API Calls

This repository contains a Python script for logging OpenAI API calls, including chat completions and embeddings, to a SQLite database. The logs can be safely written in a multi-threaded environment using a `Lock` to serialize write access to SQLite.

## Overview

This project provides a client for making chat completion and embedding requests to the OpenAI API and logs the details of each request and response to a SQLite database. The main features include:
- Logs input and output token counts and request time for chat completions.
- Logs input texts, tokens, and request time for embeddings.
- Thread-safe logging using Python's `threading.Lock`.
- Configuration via a `.env` file.
- Functionality to export logs from the SQLite database to JSONL files.
- Support for batched embedding requests.

## Configuration

### .env File

Create a `.env` file in the root directory of your project with the following content:

```ini
OPENAI_API_KEY=your_openai_api_key
MODEL_CHAT_COMPLETION=gpt-4o
MODEL_EMBEDDING=text-embedding-3-small
SQLITE_FILE=logs.db
```

- `OPENAI_API_KEY`: Your OpenAI API key.
- `MODEL_CHAT_COMPLETION`: The OpenAI model to use for chat completions (e.g., `gpt-4o`).
- `MODEL_EMBEDDING`: The OpenAI model to use for embeddings (e.g., `text-embedding-3-small`).
- `SQLITE_FILE`: The path to the SQLite database file.

## Usage

### Example Code

```python
from openai_api_logger import chat_completion, embed, dump_logs_to_jsonl

# Chat completion example
generated_text, input_tokens, output_tokens, time_taken = chat_completion(
    [{'content': "What's up?", 'role': 'user'}],
    temperature=0, max_tokens=1024, top_p=1, frequency_penalty=1
)

# Embedding example
texts = ["Hello, world!", "OpenAI is amazing"]
embeddings = embed(texts, batch=2)

# Export logs
dump_logs_to_jsonl('logs_directory')
```

### What Will Be Logged

The script logs information in two separate tables:

1. `chat_completion_logs`: Logs for chat completion requests
2. `embedding_logs`: Logs for embedding requests

#### Chat Completion Log Example

```json
{
  "id": 1,
  "timestamp": "2024-06-05 00:51:58",
  "input_messages": "[{\"content\": \"What's up?\", \"role\": \"user\"}]",
  "max_tokens": 1024,
  "temperature": 0.0,
  "top_p": 1.0,
  "frequency_penalty": 1.0,
  "output_text": "Hello! I'm here to help with any questions or information you need. What's on your mind?",
  "input_tokens": 10,
  "output_tokens": 19,
  "time_taken": 0.798882007598877
}
```

#### Embedding Log Example

```json
{
  "id": 1,
  "timestamp": "2024-06-05 00:52:10",
  "input_texts": "[\"Hello, world!\"]",
  "model": "text-embedding-3-small",
  "tokens": 4,
  "time_taken": 0.5123456789
}
```

### Dumping Logs to JSONL

To export the logs from the SQLite database to JSONL files, use the `dump_logs_to_jsonl` function:

```python
dump_logs_to_jsonl('logs_directory')
```

This will create separate JSONL files for each table in the specified directory, with each log entry represented as a JSON object on a new line.



## Contributing

Feel free to fork this repository and submit pull requests if you have any improvements or new features to add.
# openai-api-logger
