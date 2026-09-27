# Demo Recording Script (3–5 minutes)

This is a shot list to record the required screen-recorded demo. Everything it
walks through is real, backed by the running system — nothing here is a slide.
Run `docker compose up --build` (or the local dev setup in the README) and log in
as `admin` before you start recording. Keep narration brief; the point is to show
the system working, not to talk over it.

## Before you hit record

- Backend and frontend both running, seed data loaded (5 cameras, 6 watchlist
  entries — this happens automatically).
- Leave the analytics simulator running (default) so detections and alerts appear
  live during the recording without you having to trigger anything manually.
- Have two browser tabs ready: one on the dashboard, one you'll use to show the
  `/docs` API page.

## Shot list

**1. Camera onboarding (30s)**
- Cameras page → "+ Add camera". Fill in a new camera (any protocol — `simulator`
  is simplest) and save it.
- Point out it now appears in the table *and* on the map immediately.

**2. Dashboard & map (30s)**
- Switch to the Dashboard. Call out: camera counts (online/degraded/offline),
  active/critical alert counts, the map with status-colored markers, the live
  camera grid.

**3. Live / near-live feed (20s)**
- Point at the live camera tiles actually playing (C001/C003 simulator, C002
  looped recorded clip). Open one in the preview modal from the Cameras page.

**4. AI detection event (25s)**
- Scroll to "Recent detection events" on the dashboard and let a couple of new
  rows arrive live (the built-in simulator posts one every few seconds through the
  same `/events/ingest` endpoint a real model would use).

**5. Watchlist match → real-time alert (30s)**
- Open the Watchlist page, show a couple of seeded records (a stolen vehicle, a
  blacklisted vehicle).
- Switch to the Alerts page and let a live one land (or, if you want a guaranteed
  hit on camera for timing, trigger one on the API docs page — see step 7 — using
  a plate you can see in the Watchlist table). Show severity, status, and click
  Acknowledge then Resolve.

**6. Entity search & movement history (30s)**
- Vehicle Trace page → search the plate you just triggered (or any plate visible
  in the recent-events table with more than one sighting).
- Show the numbered map route and the movement-history table underneath.

**7. One API/backend workflow (30s)**
- Switch to the `/docs` tab. Show `POST /api/v1/events/ingest` — authorize with a
  token (copy it from the browser's dev tools / the login response, or just show
  the schema), fire one request with a plate that matches a watchlist entry, and
  flip back to the dashboard to show the alert land within a second or two.

**8. Architecture & scalability, briefly (30–45s)**
- Show `docs/architecture-diagram.svg` (or the rendered image in README). In one
  or two sentences: camera sources go through a common adapter interface, events
  flow through one ingest path shared by the demo simulator and any real AI
  service, WebSocket (with an optional Redis backplane) pushes updates live, and
  `SCALABILITY.md` covers the path to the hackathon's ~80,000-camera target
  (edge/regional/central tiers, partitioned storage, GPU inference sized by
  concurrent streams, not camera count).

## After recording

Upload as unlisted YouTube or an accessible Drive/OneDrive link (per the
submission instructions) and include the link in your submission email.
