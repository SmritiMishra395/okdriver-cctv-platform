# Scalability & Production Deployment Note

This prototype runs one backend instance, one Postgres database and a handful of
simulated cameras. This note explains how the same architecture extends toward the
Gujarat Police Innovation Hackathon's reference scale (~80,000 cameras) without a
redesign — which pieces already support it today, and what would be added.

## 1. Central, regional and edge processing

- **Today**: one central backend does everything — ingest, matching, dashboard API.
- **At scale**: a three-tier topology, matching the hackathon's reference models
  (VMS Federation / Central VMS):
  - **Edge** (at or near each camera cluster / police station): a lightweight
    gateway does motion-gated frame capture and, where hardware allows, first-pass
    inference (person/vehicle detection) so only *events* — not raw video — leave
    the edge under normal conditions. This is where a low-bandwidth link pays off
    most: a plate-read event is a few hundred bytes; a video stream is megabits.
  - **Regional**: aggregates several edge sites, does heavier inference (ANPR,
    re-identification) that doesn't need central compute, and forwards
    normalized events to the central platform over a persistent, resumable link.
  - **Central** (this codebase): watchlist correlation, cross-camera trace,
    dashboard, audit, long-term storage. Because ingest is already a single typed
    API contract (`POST /events/ingest`), a regional node is just another caller
    of it — no protocol change needed to add this tier.

## 2. Horizontal scaling & load balancing

- The backend is already stateless per request (JWT, no server-side session) other
  than the WebSocket connection registry, which is why `ConnectionManager`
  supports a Redis Pub/Sub backplane (`REDIS_URL`): run N backend replicas behind a
  standard load balancer (Nginx/ALB/Cloud Load Balancing), and a WebSocket client
  connected to replica A still receives an alert generated on replica B.
- Camera *video* streaming is the one workload that benefits from sticky routing
  (a given MJPEG/WebRTC session should stay on the instance that opened the
  camera's decode session) — the load balancer would pin by camera ID for stream
  routes and round-robin everything else.
- Database access would move from the current synchronous SQLAlchemy session (fine
  at prototype scale) to a connection-pooled, async driver, with read replicas for
  the dashboard's read-heavy queries (stats, search, trace) separated from the
  write path (ingest).

## 3. Video bandwidth & low-bandwidth strategies

- MJPEG (used here) is simple and universally compatible but bandwidth-heavy;
  production would use WebRTC for interactive live view (adaptive bitrate, much
  lower latency) and HLS for anything that tolerates a few seconds of delay
  (recording playback, multi-viewer fan-out via a CDN edge).
- For genuinely constrained links (rural check-posts, cellular backhaul): send
  events, not video, by default; pull a short video clip on demand only when an
  operator opens that specific camera, and drop resolution/frame rate adaptively
  based on measured link quality (the adapter interface already isolates "how do
  we get frames" from everything else, so this is a new adapter, not a rewrite).

## 4. Database indexing & scaling

- Already indexed on every query path used today: `detection_events(camera_id,
  timestamp)` and `(vehicle_number, timestamp)` for trace/search, `alerts(status,
  timestamp)` for the active-alerts view, `watchlist_entries(identifier_type,
  identifier_value)` for the match lookup.
- At 80,000 cameras, `detection_events` is the table that grows without bound —
  time-based partitioning (monthly/weekly) keeps indexes small and makes retention
  a cheap `DROP PARTITION` instead of a slow `DELETE`. Watchlist and camera tables
  stay small regardless of scale and don't need this.
- Read replicas for dashboard/search/reporting queries; the write path (ingest +
  watchlist match) stays on the primary.

## 5. Caching & message queues

- **Cache**: watchlist lookups are the hottest read on the ingest path and the
  table is comparatively small — an in-memory or Redis-cached copy, refreshed on
  write, removes a database round-trip from the ingest hot path entirely.
- **Queue**: ingest is currently synchronous (validate → store → match → broadcast
  in one request). At high event volume, ingest would instead publish to a queue
  (Kafka/RabbitMQ — already listed as an accepted mechanism in the brief) and a
  pool of worker processes would consume it, so a burst of detections can't back
  up the API itself. Redis Pub/Sub (used today for the WebSocket backplane) is
  the right tool for *fan-out*; a durable queue is the right tool for
  *ingest under load with replay/retry*, and the two would coexist.

## 6. GPU / accelerator requirements

- This prototype does no inference (per the brief) — it's the interface an
  inference service calls into. At scale, GPU need is proportional to the number
  of camera-streams needing real-time inference, not to database or API load:
  - Edge/regional inference (ANPR, detection): commodity inference accelerators
    (e.g. NVIDIA Jetson-class at the edge, T4/L4-class GPUs regionally) sized by
    concurrent-stream throughput of the chosen model, not by camera count directly
    (motion gating and frame sampling reduce effective load well below 1 GPU per
    camera).
  - Central platform: no GPU required — it only ever receives structured events.

## 7. Hot, warm and cold storage

- The schema already has a `storage_tier` (hot/warm/cold) and `retention_days`
  field per camera, deliberately, so this policy is data-driven rather than
  hard-coded:
  - **Hot** (fast disk, short retention): cameras at high-priority junctions —
    quick access for active investigations.
  - **Warm** (object storage, e.g. S3-class, standard tier): most cameras' recent
    footage.
  - **Cold** (archival/glacier-class): long-term retention for compliance, rarely
    accessed, retrieved on demand.
- Detection *events* (small, structured) live in Postgres regardless of the
  camera's video storage tier; *video* itself would live in object storage with
  the tier/retention read from this same field, not duplicated policy logic.

## 8. Monitoring, logging & health checks

- `HeartbeatService` already gives per-camera health (online/degraded/offline)
  end-to-end today, not just a container-level check.
- `/health` is a liveness endpoint suitable for a load balancer or Kubernetes
  probe today; readiness would add DB/Redis connectivity checks.
- At scale: structured logs shipped to a central store, request tracing
  (OpenTelemetry) through ingest → match → alert → WebSocket broadcast so a slow
  alert can be diagnosed by hop, and Prometheus metrics (ingest rate, match rate,
  alert latency, WebSocket connection count, per-camera health) visualized in
  Grafana — listed as an optional feature in the brief and a natural next step.

## 9. High availability & disaster recovery

- Stateless backend replicas behind a load balancer (see §2) give API-level HA
  immediately.
- Postgres: managed HA (RDS Multi-AZ or equivalent) with automated failover;
  point-in-time recovery from continuous WAL archiving.
- Redis: used only as a Pub/Sub backplane and cache in this design (never the
  system of record), so it can fail and restart without data loss — events still
  land safely in Postgres via the ingest path.
- Cross-region backup of the database and object storage for disaster recovery;
  RTO/RPO targets driven by how critical real-time alerting uptime is judged to be
  for the deployment (e.g. minutes for a law-enforcement watchlist system).

## 10. Cybersecurity & network segmentation

- Already in this prototype: JWT auth + RBAC on every mutating endpoint, bcrypt
  password hashing, Fernet-encrypted stream credentials at rest (never returned in
  plaintext), audit logging of sensitive actions, rate limiting on login and
  ingest, environment-based secrets (nothing committed).
- At scale: cameras and edge gateways sit on an isolated network segment/VLAN with
  no direct internet egress, reaching the platform only through a small number of
  authenticated ingest gateways; the management plane (this dashboard/API) sits
  behind its own segment with access restricted to operator networks/VPN; TLS
  everywhere in transit; secrets in a managed vault (not `.env` files) with
  rotation; a WAF in front of public-facing endpoints.

## 11. Estimated infrastructure and operational costs

Indicative only — real numbers depend on the cloud, region, model choice and
negotiated rates. Ballpark shape of the cost curve as the deployment grows:

| Scale | Cameras | Dominant cost | Rough monthly infra shape |
|---|---|---|---|
| Prototype (this repo) | 5 | negligible | single small VM / free-tier managed Postgres |
| Pilot | ~500 | edge compute + storage | tens of small edge boxes, one mid-size DB, modest object storage |
| District rollout | ~10,000 | GPU inference (regional) + bandwidth | GPU inference nodes become the largest line item; storage tiering matters a lot here |
| Target scale | ~80,000 | GPU inference + storage (hot/warm/cold) + egress | inference and storage dominate; API/DB layer is comparatively small once partitioned and cached, because it only ever carries *events*, not video |

The single biggest lever on cost at scale is keeping raw video off the central
path — every design choice above (edge inference, event-only ingest, tiered
storage, motion-gated capture) is aimed at making the platform's cost scale with
*events* and *retention policy*, not with *camera count × constant bitrate*.
