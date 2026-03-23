# csv-job-platform

Starter FastAPI service for ingesting and processing CSV-backed job platform data.

## Project layout

```text
csv-job-platform/
├── app/
│   ├── api/
│   │   └── routes/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── processors/
│   ├── schemas/
│   ├── services/
│   └── tasks/
├── alembic/
├── docker/
├── scripts/
├── tests/
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Getting started

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the environment template:

```bash
cp .env.example .env
```

4. Run the development server:

```bash
uvicorn app.main:app --reload
```

## PostgreSQL and migrations

Start PostgreSQL locally with Docker Compose:

```bash
docker compose up -d postgres redis
```

Create the database schema:

```bash
alembic upgrade head
```

## Environment variables

The app loads settings from environment variables and `.env` using `pydantic-settings`.

- `APP_NAME`: FastAPI application title
- `APP_ENV`: Runtime environment, such as `development` or `production`
- `APP_DEBUG`: Enables FastAPI debug mode
- `API_PREFIX`: Prefix for API routes
- `HOST`: Server bind address
- `PORT`: Server port
- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection URL
- `CELERY_BROKER_URL`: Celery broker URL
- `CELERY_RESULT_BACKEND`: Celery result backend URL

## Available endpoints

- `GET /` returns app metadata
- `GET /api/health` returns a simple health check response
- `POST /api/auth/register` creates a user account
- `POST /api/auth/login` returns a bearer token
- `GET /api/auth/me` returns the authenticated user
- `POST /api/files` uploads a CSV for the authenticated user
- `POST /api/jobs` creates a job for an owned uploaded file
- `GET /api/jobs` returns the authenticated user's paginated job history
- `GET /api/jobs/{job_id}` returns owned job status
- `GET /api/jobs/{job_id}/result` returns the owned job result

## Authentication flow

Register with email and password:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"supersecret"}'
```

Log in to get a bearer token:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"supersecret"}'
```

Call a protected endpoint:

```bash
curl http://127.0.0.1:8000/api/auth/me \
  -H "Authorization: Bearer <access-token>"
```

Upload a CSV file:

```bash
curl -X POST http://127.0.0.1:8000/api/files \
  -H "Authorization: Bearer <access-token>" \
  -F "upload=@sample.csv;type=text/csv"
```

Uploads are stored on disk under `UPLOAD_DIR` and file metadata is persisted in PostgreSQL with the authenticated user's `user_id`.

Create a summarize job for an uploaded file:

```bash
curl -X POST http://127.0.0.1:8000/api/jobs \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"file_id":1,"job_type":"summarize"}'
```

Run a Celery worker:

```bash
celery -A app.tasks.celery_app.celery_app worker --loglevel=info
```

## Database models

- `User`
- `File`
- `Job`
- `JobResult`
