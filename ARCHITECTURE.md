# Architecture

![Architecture diagram](docs/architecture-diagram.svg)

## Design goal

The brief asks for the software layer that connects live video, APIs, AI events,
databases, alerts, maps and operators into one platform — not a trained CV model.
Everything here is built so that each of those pieces can be swapped for a real
one (a real camera, a real AI model, a real message queue) without touching the
others. That's the reasoning behind the adapter interface, the single ingest code
path, and the event bus described below.

## Data flow (the assignment's "minimum end-to-end flow", concretely)

1. **Admin adds a camera** — `POST /api/v1/cameras`. The plaintext `stream_ref`
   (a URL or a path) is encrypted with Fernet before it touches the database; the
   API never echoes it back in plaintext, only a masked form.
2. **It appears in the registry and map** — `GET /api/v1/cameras` powers both the
   table and the Leaflet map (`MapView.jsx`); markers are colored by live status.
3. **Camera status is monitored** — `HeartbeatService` (`app/services/heartbeat.py`)
   runs every 8 seconds, resolves the camera's adapter from its `source_protocol`,
   and calls `adapter.health_check()` with a timeout. A changed status is written to
   the database *and* broadcast over WebSocket immediately — the dashboard doesn't
   poll for this.
4. **A live/recorded feed is viewable** — `GET /api/v1/cameras/{id}/stream` wraps
   whichever adapter is registered for that camera in a single MJPEG
   (`multipart/x-mixed-replace`) response, so the same `<img>` tag on the frontend
   works whether the source is the procedural simulator, a looped file, or a real
   RTSP camera.
5. **An analytics service produces a detection event** — either the built-in
   `AnalyticsSimulator` background task (standing in for a real CV pipeline) or an
   external service calls `POST /api/v1/events/ingest` with the same payload shape
   (`camera_id, timestamp, vehicle_number, confidence, vehicle_type, bounding_box,
   event_type`) given as the example in the brief.
6. **Backend validates and stores it** — Pydantic validates the payload; a
   time-windowed hash (`_dedup_hash` in `services/ingest.py`) collapses duplicate
   detections of the same identifier from the same camera within a configurable
   window (default 10s), so a jittery detector can't flood the system.
7. **The event is checked against the watchlist** — a single indexed lookup on
   `(identifier_type, identifier_value)`.
8. **A match generates a real-time alert** — an `Alert` row is written and
   broadcast over WebSocket (`alert.new`) to every connected dashboard the moment
   it happens, with camera, location, matched entity, confidence and timestamp.
9. **The operator searches the entity and sees movement history** —
   `GET /api/v1/entities/search` (autocomplete-style) and
   `GET /api/v1/trace/{identifier}` return every camera hit in chronological order,
   which the frontend renders as a numbered route with a polyline on the map.
10. **The system keeps an auditable history** — every create/update/disable/
    acknowledge/resolve action writes an `AuditLog` row (actor, action, entity,
    details, timestamp), queryable by an admin.

## Why these specific choices

**One adapter interface for every camera type.** `app/video/base.py` defines
`frames()` and `health_check()`; `registry.py` maps `source_protocol` to a concrete
class. Adding a real vendor SDK later is "write one more adapter class", not
"change the stream endpoint, the health check, and the frontend player". The RTSP
adapter is a genuine, working implementation (OpenCV + FFmpeg) — it's registered
against a non-routable test address in the seed data because no physical camera is
reachable from a grading environment, not because the code is a stub.

**One ingest function for simulated and real analytics.** Whether a detection comes
from the demo simulator or a real model server, it goes through the exact same
`services/ingest.py:ingest_event()` — validation, dedup, storage, watchlist match,
broadcast. Swapping the simulator for a real inference service later is a
configuration change (`ENABLE_ANALYTICS_SIMULATOR=false`), not a rewrite.

**WebSocket with an optional Redis backplane, not polling.** A single
`ConnectionManager` (`app/realtime/ws_manager.py`) broadcasts to every connected
dashboard. With `REDIS_URL` unset it broadcasts in-process (zero extra
infrastructure for the prototype); with it set, every broadcast is published to a
Redis channel and relayed back out to each replica's local sockets, which is what
makes horizontal scaling to multiple backend instances behind a load balancer
possible without operators on different instances missing each other's events.

**Encrypted-at-rest stream credentials, masked in every response.** A camera's
`stream_ref` can embed a username/password (`rtsp://user:pass@host/...`). It's
encrypted with Fernet before being written to the database and decrypted only at
the point of use (opening the adapter); every API response shows
`rtsp://***:***@host/...` instead.

**PostgreSQL by default, no Postgres-only features used.** The models use only
portable SQLAlchemy types, so the same schema (and the same Alembic migration)
works against SQLite for a zero-setup local trial or RDS-managed PostgreSQL in
a real deployment.

## Where the pieces live

See the "Repository layout" section of [README.md](README.md) for the file tree.
The [ER diagram](docs/er-diagram.svg) covers the six tables and their foreign keys;
[SCALABILITY.md](SCALABILITY.md) covers how this evolves toward the hackathon's
~80,000-camera target.
