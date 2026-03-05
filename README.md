# Organization Manager API

Multi-tenant organization management backend service.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0 (async)
- PostgreSQL 16
- Docker

## Quick Start

```bash
docker compose up --build
```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

## Project Structure

```
app/
├── api/v1/endpoints/   # API routes
├── core/               # Config, security
├── db/                 # Database session
├── models/             # SQLAlchemy models
├── schemas/            # Pydantic schemas
├── services/           # Business logic
└── middleware/         # Custom middleware
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | No (has default) |
| `SECRET_KEY` | JWT signing key | No (has default for dev) |
| `GEMINI_API_KEY` | Google Gemini API key | Only for chatbot |
