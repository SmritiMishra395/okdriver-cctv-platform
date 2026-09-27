# okDriver — CCTV Monitoring, Video Analytics & Real-Time Alert Platform

A working prototype of a centralized CCTV monitoring platform: camera registry with
map and health monitoring, live/simulated video feeds through a pluggable adapter
layer, an ANPR-style analytics ingest pipeline, watchlist correlation with real-time
alerting, and cross-camera vehicle trace — built for the okDriver Full Stack
Developer hiring challenge (aligned with the Gujarat Police Innovation Hackathon 2026
problem statement).

Full-stack, no external services required to try it out: SQLite works out of the box,
Postgres + Redis are used for the "production-style" run via Docker Compose.

## Contents

- [Quick start](#quick-start)
- [Demo accounts](#demo-accounts)
- [What's implemented](#whats-implemented)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Environment variables](#environment-variables)
- [Database](#database)
- [API](#api)
- [Real-time events](#real-time-events)
- [Video sources](#video-sources)
- [Security](#security)
- [Tests](#tests)
- [Known limitations](#known-limitations--what-id-do-with-more-time)

## Quick start

### Option A — Docker Compose (Postgres + Redis, closest to production)

```bash
cp backend/.env.example backend/.env
# edit backend/.env: set JWT_SECRET_KEY and CREDENTIAL_ENCRYPTION_KEY (see comments in the file)
docker compose up --build
```

- Backend: http://localhost:8000 (docs at `/docs`, health at `/health`)
- Frontend: http://localhost:5173
- The `seed` service runs once automatically and populates 5 demo cameras and 6
  watchlist records (see [`backend/scripts/seed.py`](backend/scripts/seed.py)).

### Option B — Run locally without Docker (SQLite, fastest to try)

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # paste into CREDENTIAL_ENCRYPTION_KEY in .env
sed -i 's#^DATABASE_URL=.*#DATABASE_URL=sqlite:///./okdriver.db#' .env   # or leave the Postgres URL if you have Postgres running
python scripts/generate_sample_video.py     # creates the synthetic "checkpoint" clip used by camera C002
uvicorn app.main:app --reload
# in another terminal
python scripts/seed.py

# frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and sign in (see below). The backend also starts a
built-in analytics simulator and heartbeat service, so the dashboard fills with
live detections, alerts and camera health changes within a few seconds — no manual
steps needed to see the real-time flow.

## Demo accounts

| Username | Password | Role | Can do |
|---|---|---|---|
| `admin` | `Admin@12345` | admin | Everything: manage cameras, watchlist, view audit log |
| `operator` | `Operator@12345` | operator | Monitor dashboard, search/trace, acknowledge & resolve alerts |

Change these in `.env` before deploying anywhere reachable by others.

## What's implemented

Everything in the assignment's "Minimum End-to-End Flow" runs, end to end, against
real backend state (not mocked screens):

- **Camera registry** — add/edit/disable/search/filter, department & zone, storage
  tier & retention, manual or API onboarding, per-camera audit trail, map view.
- **Live video** — two *logically different* source types wired up for real
  (`simulator`, looped `file`), plus a fully functional `rtsp` adapter and an
  `onvif` discovery stub, so the architecture already accepts real RTSP/ONVIF
  cameras without further changes. See [Video sources](#video-sources).
- **AI analytics ingest** — `POST /api/v1/events/ingest` validates, deduplicates
  (time-windowed hash, see `services/ingest.py`) and stores ANPR-style detection
  events, exactly the same path used by the built-in analytics simulator.
- **Watchlist correlation & real-time alerts** — every ingested vehicle plate is
  checked against the watchlist; a match creates an `Alert` and pushes it to every
  connected dashboard over WebSocket immediately.
- **Vehicle / entity trace** — search a plate, see every camera it was detected at,
  in order, plotted as a route on the map.
- **Unified dashboard** — live stats, camera map, live camera grid, active alerts,
  recent events, all updating without a page refresh.
- **Audit log** — every create/update/disable/acknowledge/resolve action, who did it
  and when, queryable by entity type (admin-only).
- **RBAC** — `admin` vs `operator`, enforced server-side on every mutating endpoint,
  not just hidden in the UI.
- **Camera heartbeat service** — genuinely probes each camera's adapter every 8s
  (not a random flicker); the seeded data includes one camera pointed at a file that
  was never uploaded, so you can see a real, honest "Offline" status rather than a
  hard-coded one.

## Architecture

![Architecture diagram](docs/architecture-diagram.svg)

See [ARCHITECTURE.md](ARCHITECTURE.md) for the write-up (data flow, why each piece
exists, and how the "minimum end-to-end flow" maps onto it).

## Repository layout

```
backend/
  app/
    routers/        REST endpoints (auth, cameras, streams, events, watchlist, alerts, trace, stats, audit, ws)
    video/           adapter interface + simulator/file/rtsp/onvif implementations
    services/        ingest+watchlist matching, analytics simulator, heartbeat, audit
    realtime/        WebSocket connection manager (+ optional Redis Pub/Sub backplane)
    models.py        SQLAlchemy models (see docs/er-diagram.svg)
    schemas.py       Pydantic request/response models
    security.py      JWT, password hashing, Fernet credential encryption
  alembic/           database migrations (initial schema)
  scripts/           seed.py, generate_sample_video.py
  tests/             pytest suite (auth, cameras, ingest+watchlist, trace, video adapters)
  media/sample/      synthetic sample clip used by camera C002
frontend/
  src/
    pages/           Dashboard, Cameras, Watchlist, Alerts, Trace, Audit, Login
    components/      MapView (Leaflet), CameraGrid (live MJPEG tiles), AlertList, StatCard, Layout
    context/         auth context (JWT storage)
    useRealtime.js   WebSocket hook with auto-reconnect
docs/
  architecture-diagram.svg, er-diagram.svg, openapi.json
docker-compose.yml
```

## Environment variables

See [`backend/.env.example`](backend/.env.example) for the full list with comments.
The important ones:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres (recommended) or SQLite connection string |
| `JWT_SECRET_KEY` | signs access tokens — must be random and secret |
| `CREDENTIAL_ENCRYPTION_KEY` | Fernet key used to encrypt camera `stream_ref` (URLs/credentials) at rest |
| `REDIS_URL` | optional; enables the Pub/Sub backplane for multi-replica deployments |
| `ENABLE_ANALYTICS_SIMULATOR` / `ENABLE_HEARTBEAT_SERVICE` | turn off the built-in demo generators once a real AI service and real cameras are wired up |

No secret ever has a real value committed to this repository; `.env` is
git-ignored and only `.env.example` (placeholder values) is tracked.

## Database

PostgreSQL by default (RDS-compatible: no Postgres-only extensions are used), SQLite
works unchanged for local trial. Schema is managed two ways:

- **Quick start**: the app creates tables automatically on boot
  (`AUTO_CREATE_TABLES=true`, the default) — nothing to run manually.
- **Production-style**: set `AUTO_CREATE_TABLES=false` and run
  `alembic upgrade head` as a deploy step. The initial migration
  (`alembic/versions/*_initial_schema.py`) was autogenerated from the same
  SQLAlchemy models, so both paths produce an identical schema.

Six tables, all indexed on their query paths (camera+timestamp, vehicle+timestamp,
alert status, watchlist identifier). Diagram: [docs/er-diagram.svg](docs/er-diagram.svg).

## API

Interactive OpenAPI/Swagger docs are served by the running backend at `/docs`
(ReDoc at `/redoc`). A static export of the same spec is checked in at
[docs/openapi.json](docs/openapi.json) for offline review.

Core endpoints:

```
POST   /api/v1/auth/login
GET    /api/v1/auth/me

GET    /api/v1/cameras                      list / search / filter
POST   /api/v1/cameras                      create (admin)
PATCH  /api/v1/cameras/{id}                 update (admin)
POST   /api/v1/cameras/{id}/disable|enable  (admin)
GET    /api/v1/cameras/{id}/audit           per-camera audit history
GET    /api/v1/cameras/{id}/stream          MJPEG live/simulated feed
GET    /api/v1/cameras/{id}/snapshot        single JPEG frame
GET    /api/v1/onvif/discover               ONVIF discovery (mock)

POST   /api/v1/events/ingest                AI analytics event ingest
GET    /api/v1/events                       recent events (filterable)

GET    /api/v1/watchlist                    list / search
POST   /api/v1/watchlist                    create (admin)
PATCH  /api/v1/watchlist/{id}               update (admin)
DELETE /api/v1/watchlist/{id}               deactivate (admin)

GET    /api/v1/alerts                       list / filter
PATCH  /api/v1/alerts/{id}                  acknowledge / resolve

GET    /api/v1/entities/search?q=           search seen identifiers
GET    /api/v1/trace/{identifier}           full movement history + watchlist status

GET    /api/v1/stats/summary                dashboard counters
GET    /api/v1/audit                        audit log (admin)

WS     /ws?token=...                        real-time event stream
```

## Real-time events

WebSocket at `/ws`, one connection per dashboard session, broadcasting
`event.new`, `alert.new`, `alert.updated`, `camera.status_changed`. When
`REDIS_URL` is set, every broadcast is published to a Redis channel and relayed
back out to each replica's locally-connected sockets — so the event bus stays
consistent if the backend is scaled to multiple instances behind a load balancer
(single-instance in-process broadcast is the default and needs no Redis).
Ingested events are deduplicated inside a short time window per camera+identifier
so a jittery detector can't flood the dashboard or the alert feed.

## Video sources

Camera sources plug into one common interface (`app/video/base.py`:
`frames()` + `health_check()`), selected by `camera.source_protocol`:

| Protocol | What it is | Used by |
|---|---|---|
| `simulator` | procedurally generated junction scene (Pillow) | C001, C003 |
| `file` | loops a recorded clip via OpenCV | C002 |
| `rtsp` | real RTSP/FFmpeg adapter | C005 (points at a non-routable test address so it fails safely in this environment — swap in a real URL and it works unchanged) |
| `onvif` | resolves to `rtsp` after `onvif_adapter.discover()` (mocked; a real deployment would use WS-Discovery) | — |

No real CCTV footage ships with this submission — none was available under a
license clear for redistribution — so C002's clip is a small synthetic pattern
generated by `scripts/generate_sample_video.py` (FFmpeg `lavfi` test source),
not stock footage.

## Security

- JWT bearer auth, bcrypt password hashing, role-based authorization enforced on
  every mutating endpoint (`require_admin` dependency), not just hidden in the UI.
- Camera `stream_ref` (which may embed credentials) is encrypted at rest with
  Fernet and never returned in plaintext — API responses only ever show a masked
  value (`rtsp://***:***@host/...`).
- Rate limiting on `/auth/login` and `/events/ingest` (slowapi).
- Every create/update/disable/acknowledge/resolve action is written to the audit
  log with actor, timestamp and details.
- CORS is restricted to configured origins; all configuration is environment-based;
  no secret has a committed real value.
- HTTPS/TLS is expected to terminate at a reverse proxy/load balancer in front of
  this service (see [SCALABILITY.md](SCALABILITY.md)) — not handled by the app
  process itself, which is standard practice behind Nginx/ALB/Cloud Load Balancing.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

25 tests covering auth, RBAC, camera CRUD + audit trail, ingest validation,
deduplication, watchlist matching → alert creation, alert acknowledge/resolve,
vehicle trace, and a regression test for a real stability issue hit while building
the RTSP adapter (see [Known limitations](#known-limitations--what-id-do-with-more-time)).
CI (`.github/workflows/ci.yml`) runs the same suite plus a frontend build on every push.

## Known limitations / what I'd do with more time

- **RTSP health checks run one blocking OpenCV/FFmpeg call per tick via a thread.**
  While building the heartbeat service I hit a real incident: `cv2.VideoCapture()`
  against an unreachable host can block inside native code for a long time without
  releasing control back to asyncio, which is able to stall the *entire* event loop
  (not just that one request) even when dispatched through `asyncio.to_thread`. The
  fix in this repo (`app/video/rtsp_adapter.py`) does a raw TCP pre-check with a
  proper socket timeout before ever calling into OpenCV, which is safe and is
  covered by a regression test (`tests/test_video_adapters.py`). With more time I'd
  move this probe into a small dedicated worker (or a process pool) so a genuinely
  hung native call can be hard-killed rather than merely avoided.
- **Watchlist correlation is implemented for vehicle plates (ANPR)**, matching the
  assignment's worked example end to end. Person/face-based watchlist entries
  (`identifier_type=face_id`) can already be created and managed in the UI, but live
  correlation against them needs a face-recognition event source publishing to the
  same `/events/ingest` path — the matching code path is identical, it's just not
  exercised by the current simulator.
- **No production alerting fan-out** (SMS/push/email) — alerts currently only reach
  connected dashboard sessions over WebSocket. Would add a notification worker
  consuming the same event stream.
- **Single-process rate limiting** (in-memory `slowapi`) is fine for one instance;
  a multi-replica deployment needs a shared store (Redis-backed limiter).
- **Route reconstruction is straight-line, chronological** between camera points —
  no road-network snapping. Good enough to show direction of travel; a real
  deployment would snap to a routing graph.
- No automated frontend tests yet (backend has 25); would add Playwright
  component/e2e coverage next.
