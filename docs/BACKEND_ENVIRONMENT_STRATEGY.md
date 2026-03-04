# Backend Environment and Secrets Strategy

This document defines environment profiles, required variables, and secret handling for Pallet Manager 2.0 backend.

## Environment Profiles

Use one `.env` file per deployment target:

- Local: `backend/.env.local` (developer machine; not committed)
- Dev/QA: managed by deployment environment or secret manager
- Prod: managed by deployment environment or secret manager

For local bootstrapping, copy:

```bash
cd backend
cp .env.example .env
```

## Environment Variable Matrix

| Variable | Local | Dev/QA | Prod | Secret |
| --- | --- | --- | --- | --- |
| `APP_NAME` | required | required | required | no |
| `APP_ENV` | required | required | required | no |
| `APP_HOST` | required | required | required | no |
| `APP_PORT` | required | required | required | no |
| `DATABASE_URL` | required | required | required | yes |
| `JWT_SECRET` | required | required | required | yes |
| `JWT_ALGORITHM` | required | required | required | no |
| `JWT_ACCESS_TOKEN_MINUTES` | required | required | required | no |
| `MINIO_ENDPOINT` | required | required | required | no |
| `MINIO_ACCESS_KEY` | required | required | required | yes |
| `MINIO_SECRET_KEY` | required | required | required | yes |
| `MINIO_BUCKET_EXPORTS` | required | required | required | no |
| `MINIO_BUCKET_IMPORTS` | required | required | required | no |
| `MINIO_SECURE` | required | required | required | no |
| `SEED_ADMIN_USERNAME` | optional | optional | optional | no |
| `SEED_ADMIN_EMAIL` | optional | optional | optional | no |
| `SEED_ADMIN_PASSWORD` | required for seed scripts | required for seed scripts | required for seed scripts | yes |

## Secret Handling Rules

- Do not hardcode runtime secrets in application code.
- Do not commit real credentials in `.env` files.
- Store secrets in a secret manager or CI/CD protected variables for non-local environments.
- Rotate secrets on compromise or role changes.

## Rotation Process

1. Generate new credential/secret in the backing system (database, JWT secret, MinIO key).
2. Update deployment environment variables.
3. Restart backend services to pick up new values.
4. Validate `/health/live` and key API flows.
5. Revoke old credentials.

## Startup With Environment Only

The backend now requires environment-provided values for:

- `DATABASE_URL`
- `JWT_SECRET`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`

If any are missing, startup fails fast during settings load.
