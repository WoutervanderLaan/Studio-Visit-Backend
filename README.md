ZakBot FastApi Test

A FastApi backend which hosts a small llm that identifies as Zak Bagans from Ghost Adventures. 

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
uvicorn app:app --reload 
```

Uvicorn running on http://127.0.0.1:8000 


## OpenAPI docs

http://127.0.0.1:8000/docs#/