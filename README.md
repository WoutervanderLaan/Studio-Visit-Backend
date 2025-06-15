# Studio Visit Backend

A FastApi backend for the drawing app at https://woutervanderlaan.com/canvas

## Getting Started

First, set up virtual environment:

```bash
python -m venv .venv
```

Then, initiate virtual environment:

```bash
source .venv/bin/activate
```

Lastly, install dependencies:

```bash
pip install -r requirements.txt
```

## Running server

```bash
uvicorn main:app --host localhost --port 8000 --reload
```

Uvicorn running on http://localhost:8000

## OpenAPI docs

http://127.0.0.1:8000/docs#/
