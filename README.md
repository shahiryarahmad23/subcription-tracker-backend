# Subscription Tracker API

HTTP API for user accounts and the subscriptions those accounts own. The base URL in local development is `http://127.0.0.1:8000`. Request and response bodies are JSON. Interactive docs are at `/docs`.

Protected routes require:

```http
Authorization: Bearer <access_token>
```

The access token is a JWT and expires in 15 minutes. The refresh token is an opaque string and is only sent to logout. CORS allows `http://localhost:5173` and does not use cookies.

## Endpoints

### Health

| Method | Path | Who | Success |
| --- | --- | --- | --- |
| `GET` | `/health` | Public | `200` `{ "status": "ok" }` |

### Accounts

| Method | Path | Who | Success | What it does |
| --- | --- | --- | --- | --- |
| `POST` | `/user/register` | Public | `201` user | Create an account. `password` is stored as a hash. `role` may be omitted (`user`) or set to `admin`. |
| `POST` | `/user/login` | Public | `200` tokens | Check username and password. Returns `access_token`, `refresh_token`, and `token_type`. |
| `POST` | `/user/logout` | Signed in | `204` empty | Body is `{ "refresh_token": "..." }`. Revokes that refresh session. |
| `GET` | `/user/` | Admin | `200` user list | Every account: `id`, `username`, `email`, `role`, `is_active`. |
| `GET` | `/user/{user_id}/subscriptions` | Admin | `200` subscription list | Subscriptions owned by that user, including the owner's username. |
| `PATCH` | `/user/{user_id}/access` | Admin | `200` user | Body is `{ "active": true \| false }`. `false` stops sign-in and revokes refresh tokens. An admin cannot change their own access. |
| `DELETE` | `/user/{user_id}` | Admin | `204` empty | Deletes the account, its refresh tokens, and its subscriptions. An admin cannot delete their own account. |

Register body:

```json
{
  "username": "ada",
  "password": "secret",
  "email": "ada@example.com",
  "dob": "1990-04-01",
  "role": "user"
}
```

`dob` is a calendar date (`YYYY-MM-DD`). `username` and `email` are unique.

### Subscriptions

A signed-in user works with their own subscriptions. An admin can read every subscription. Update and delete stay limited to the owner.

| Method | Path | Who | Success | What it does |
| --- | --- | --- | --- | --- |
| `POST` | `/subscriptions/` | User or admin | `201` subscription | Creates a subscription for the token's user. Do not send `user_id`. |
| `GET` | `/subscriptions/mine` | User or admin | `200` page | The caller's subscriptions, ordered by id. Query: `cursor` (optional), `limit` (1–100, default 20). |
| `GET` | `/subscriptions/` | User or admin | `200` list | Caller sees only their rows. Admin sees every row and `user.username`. |
| `GET` | `/subscriptions/{id}` | User or admin | `200` subscription | One subscription. A user reading someone else's id gets `404`. |
| `PATCH` | `/subscriptions/` | Owner | `200` subscription | Body includes `id` and only the fields to change. |
| `DELETE` | `/subscriptions/{id}` | Owner | `204` empty | Deletes that subscription. |

Create body:

```json
{
  "service_name": "Netflix",
  "service_plan": "Premium",
  "price": "15.99",
  "currency": "USD",
  "subscription_date": "2026-01-15T00:00:00Z",
  "duration": 12
}
```

- `service_name`: `Netflix`, `Spotify`, `YouTube Premium`, `Disney+`, `Steam`, `Apple TV+`, `Claude`, or `Cursor`. Unique per user.
- `service_plan`: free text, such as `Premium` or `Family`.
- `price`: amount for one billing period, greater than 0.
- `currency`: `USD`, `EUR`, `GBP`, `CAD`, `AUD`, `JPY`, `INR`, or `PKR`.
- `subscription_date`: UTC start time, ISO 8601.
- `duration`: length in whole months, greater than 0. `12` means one year.

`GET /subscriptions/mine` returns:

```json
{
  "items": [],
  "next_cursor": null
}
```

Send `next_cursor` as the next `cursor`. `null` means the last page.

### Common errors

| Status | Meaning |
| --- | --- |
| `401` | Missing, invalid, or expired access token, or bad login / refresh token. |
| `403` | Role is not allowed, or a page cursor belongs to another user. |
| `404` | The row or the first page of results does not exist. |
| `409` | Duplicate username, email, or service name; stale page cursor; an admin acting on their own account. |
| `422` | A field is missing or not in the allowed set. `detail` is a list. |
| `500` | Database error. |

## Run locally

1. Copy `.env.example` to `.env` and set the database and token values.
2. Start Postgres:

```powershell
docker compose up -d
```

3. Apply migrations and start the API:

```powershell
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The app listens on port 8000. Postgres 16 uses the user, password, database, and port from `.env`.


