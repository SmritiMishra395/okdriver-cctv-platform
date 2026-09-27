def test_entity_search_finds_seen_vehicle(client, admin_headers):
    resp = client.get("/api/v1/entities/search?q=GJ09ZZ", headers=admin_headers)
    assert resp.status_code == 200
    results = resp.json()
    assert any(r["identifier"] == "GJ09ZZ0007" for r in results)
    hit = next(r for r in results if r["identifier"] == "GJ09ZZ0007")
    assert hit["is_watchlisted"] is True
    assert hit["sightings"] >= 1


def test_trace_returns_chronological_camera_hits(client, admin_headers):
    resp = client.get("/api/v1/trace/GJ09ZZ0007", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_watchlisted"] is True
    assert len(body["hits"]) >= 1
    timestamps = [h["timestamp"] for h in body["hits"]]
    assert timestamps == sorted(timestamps)
    assert all(h["camera_id"] == "TCAM2" for h in body["hits"])


def test_trace_unknown_identifier_returns_empty_hits(client, admin_headers):
    resp = client.get("/api/v1/trace/NOSUCHPLATE0000", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["hits"] == []
    assert body["is_watchlisted"] is False


def test_stats_summary_reflects_seeded_activity(client, admin_headers):
    resp = client.get("/api/v1/stats/summary", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["cameras_total"] >= 1
    assert body["watchlist_entries"] >= 1


def test_audit_log_requires_admin(client, operator_headers):
    resp = client.get("/api/v1/audit", headers=operator_headers)
    assert resp.status_code == 403


def test_audit_log_visible_to_admin(client, admin_headers):
    resp = client.get("/api/v1/audit", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) > 0
