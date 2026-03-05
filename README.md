# Multi-Tenant Organization Manager API

A secure, async, multi-tenant backend service for organization management with RBAC authorization.

## Tech Stack

- **Python 3.11+** - Modern Python with async support
- **FastAPI** - High-performance async web framework
- **SQLAlchemy 2.0** - Async ORM with modern Python typing
- **PostgreSQL 16** - Database with full-text search support
- **JWT** - Stateless authentication
- **Docker** - Containerized deployment

## Quick Start

```bash
# Start the application
docker compose up

# Or with rebuild
docker compose up --build
```

The API will be available at:
- **Swagger Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Project Structure

```
app/
├── main.py
├── api/
│   ├── deps.py
│   └── v1/endpoints/
├── core/
├── db/
├── models/
├── schemas/
└── services/
```

## Database Design

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│    User     │     │  Membership  │     │Organization │
├─────────────┤     ├──────────────┤     ├─────────────┤
│ id (UUID)   │──┐  │ id (UUID)    │  ┌──│ id (UUID)   │
│ email       │  └──│ user_id      │  │  │ name        │
│ password    │     │ org_id       │──┘  │ slug        │
│ full_name   │     │ role_id      │──┐  │ created_at  │
│ is_active   │     │ is_active    │  │  └─────────────┘
│ search_vec  │     │ created_at   │  │
└─────────────┘     └──────────────┘  │  ┌─────────────┐
                                      └──│    Role     │
┌─────────────┐     ┌──────────────┐     ├─────────────┤
│    Item     │     │  AuditLog    │     │ id (UUID)   │
├─────────────┤     ├──────────────┤     │ name        │
│ id (UUID)   │     │ id (UUID)    │     │ description │
│ org_id      │     │ org_id       │     └─────────────┘
│ created_by  │     │ user_id      │
│ data (JSON) │     │ action       │
│ created_at  │     │ entity_type  │
└─────────────┘     │ entity_id    │
                    │ details(JSON)│
                    │ created_at   │
                    └──────────────┘
```

### Key Design Decisions

1. **UUID Primary Keys**: More secure for multi-tenant systems, prevents ID enumeration attacks
2. **JSONB for flexible data**: Items store arbitrary JSON data, allowing flexibility
3. **Soft delete ready**: `is_active` flags on User and Membership for soft deletion
4. **Full-text search**: PostgreSQL tsvector with GIN index for efficient user search
5. **Audit trail**: All significant actions are logged with full context

## Architecture Decisions

### 1. Service Layer Pattern
Business logic is separated into service classes, keeping endpoints thin and testable.

### 2. Dependency Injection for RBAC
```python
# Role-based access control via FastAPI dependencies
require_admin = RoleChecker(["admin"])
require_member = RoleChecker(["admin", "member"])
```

### 3. Multi-tenancy Isolation
- All queries are scoped by `org_id`
- Membership is checked before any organization access
- Users can have different roles in different organizations

### 4. Async Everything
- Async SQLAlchemy with asyncpg driver
- Non-blocking database operations
- Async streaming for AI chatbot responses

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, returns JWT |

### Organizations
| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| POST | `/api/v1/organization` | Create organization | Auth |
| POST | `/api/v1/organization/{id}/user` | Invite user | Admin |
| GET | `/api/v1/organizations/{id}/users` | List users | Admin |
| GET | `/api/v1/organizations/{id}/users/search` | Search users | Admin |

### Items
| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| POST | `/api/v1/organizations/{id}/item` | Create item | Member+ |
| GET | `/api/v1/organizations/{id}/item` | List items | Member+ |

### Audit & AI
| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| GET | `/api/v1/organizations/{id}/audit-logs` | View audit logs | Admin |
| POST | `/api/v1/organizations/{id}/audit-logs/ask` | Ask AI about logs | Admin |

## Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | Configured in docker-compose |
| `SECRET_KEY` | JWT signing key | Dev default (change in production) |
| `GEMINI_API_KEY` | Google Gemini API key | Optional (for AI chatbot) |

## Running Tests

Tests use **pytest** with **testcontainers** for isolated PostgreSQL instances.

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py -v
```

### Test Coverage
- **Authentication**: Registration, login, JWT validation
- **RBAC**: Admin-only endpoints, member permissions
- **Organization Isolation**: Cross-org access prevention
- **Pagination**: All list endpoints
- **Audit Logging**: Action logging verification

## Development

### Hot Reload (Development)
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Database Migrations
Migrations run automatically on container start. To create new migrations:

```bash
# Inside the container
alembic revision --autogenerate -m "description"
```

## Security Considerations

1. **Password Hashing**: bcrypt with automatic salt
2. **JWT Tokens**: Short-lived tokens (30 min default)
3. **SQL Injection**: Prevented via SQLAlchemy ORM
4. **Organization Isolation**: Enforced at query level
5. **Input Validation**: Pydantic schemas with constraints

## Trade-offs & Future Improvements

### Current Trade-offs
- **Invite requires existing user**: Users must register before being invited (simpler flow)
- **No refresh tokens**: Single JWT strategy (simpler, but requires re-login)
- **Sync LLM calls**: AI responses block the request (could use background tasks)

### Future Improvements
- Add refresh token rotation
- Implement email invitations for non-registered users
- Add WebSocket for real-time audit log streaming
- Implement rate limiting for production
- Add Redis for caching and session management
