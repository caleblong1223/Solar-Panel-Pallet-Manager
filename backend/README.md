# Backend (FastAPI)

## Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8000
```

## Run migrations

```bash
cd backend
alembic upgrade head
```

## Environment

Copy `.env.example` to `.env` and set values.
