# Jarvis backend

FastAPI service that generates podcast episodes overnight and serves them to the
app. Built platform-agnostic: the database, object storage, auth, and the
LLM/TTS/STT models all sit behind interfaces. Vendors (Supabase, S3, OpenAI…)
are chosen by env var and implemented in one adapter each — nothing else in the
code imports a vendor SDK.

## Layout

```
app/
  config.py              # typed settings from env — the only home for vendor choices
  core/
    interfaces/          # the agnostic contracts everything codes against
      storage.py llm.py tts.py stt.py auth.py database.py
    providers.py         # factory: a config string -> a concrete adapter
  domain/entities.py     # pure dataclasses, no ORM
  adapters/              # concrete implementations, one folder per vendor kind
    db/                  # SQLAlchemy models + repositories (any Postgres)
    storage/local.py     # local-filesystem storage (default)
  services/              # generation pipeline (WIP)
  api/                   # routers (WIP)
  main.py                # FastAPI entry
alembic/                 # migrations (schema lives in this repo, not a dashboard)
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in KEY_ENCRYPTION_KEY and DATABASE_URL
```

Generate the encryption key for user BYO keys:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Database

Schema is managed with Alembic; the connection URL comes from `DATABASE_URL`
(the same setting the app uses).

```bash
alembic upgrade head          # apply migrations
alembic revision --autogenerate -m "message"   # after changing models
```

## Run

```bash
uvicorn app.main:app --reload
# http://localhost:8000/health
# http://localhost:8000/docs
```

## Design rule

If you're about to `import openai` / `boto3` / `supabase` anywhere outside
`app/adapters/<kind>/`, stop — add an adapter behind the interface instead.
