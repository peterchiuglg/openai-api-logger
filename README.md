# Client-Side Logging for OpenAI Chat Completion Calls

This repository contains a Python script for logging OpenAI chat completion calls to a SQLite database. The logs can be safely written in a multi-threaded environment using a `Lock` to serialize write access to SQLite.

## Overview

This project provides a client for making chat completion requests to the OpenAI API and logs the details of each request and response to a SQLite database. The main features include:
- Logs input and output token counts and request time for each chat completion.
- Thread-safe logging using Python's `threading.Lock`.
- Configuration via a `.env` file.
- Functionality to export logs from the SQLite database to a JSONL file.

## Configuration

### .env File

Create a `.env` file in the root directory of your project with the following content:

```ini
API_KEY=your_openai_api_key
MODEL=gpt-4o
SQLITE_FILE=logs.db
```

- `API_KEY`: Your OpenAI API key.
- `MODEL`: The OpenAI model to use (e.g., `gpt-4o`).
- `SQLITE_FILE`: The path to the SQLite database file.

## Usage

### Example Code

```python
from openai_cc import chat_completion, dump_logs_to_jsonl

generated_text, input_tokens, output_tokens, time_taken = chat_completion(
    [{'content': "What's up?", 'role': 'user'}],
    temperature=0, max_tokens=1024, top_p=1, frequency_penalty=1
)

dump_logs_to_jsonl('logs.jsonl')
```

### What Will Be Logged

When you run the above code, it will log the following information:

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

### Dumping Logs to JSONL

To export the logs from the SQLite database to a JSONL file, use the `dump_logs_to_jsonl` function:

```python
dump_logs_to_jsonl('logs.jsonl')
```

This will create a `logs.jsonl` file with each log entry represented as a JSON object on a new line.

## Contributing

Feel free to fork this repository and submit pull requests if you have any improvements or new features to add.
# openai-chat-logger
