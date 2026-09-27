CAMERA_PAYLOAD = {
    "id": "TCAM2",
    "name": "Ingest Test Camera",
    "department": "Test Traffic Dept",
    "latitude": 21.5,
    "longitude": 73.0,
    "source_protocol": "simulator",
    "stream_ref": "simulator:TCAM2:Ingest Test",
}

WATCHLIST_PAYLOAD = {
    "category": "stolen_vehicle",
    "identifier_type": "plate",
    "identifier_value": "gj 09 zz 0007",
    "label": "Test stolen vehicle record",
    "risk_level": "critical",
}


def _setup(client, admin_headers):
    client.post("/api/v1/cameras", json=CAMERA_PAYLOAD, headers=admin_headers)
    client.post("/api/v1/watchlist", json=WATCHLIST_PAYLOAD, headers=admin_headers)


def test_watchlist_identifier_is_normalized(client, admin_headers):
    _setup(client, admin_headers)
    resp = client.get("/api/v1/watchlist?q=GJ09", headers=admin_headers)
    assert resp.status_code == 200
    entries = resp.json()
    assert any(e["identifier_value"] == "GJ09ZZ0007" for e in entries)


def test_ingest_event_without_match_creates_no_alert(client, admin_headers):
    payload = {
        "camera_id": "TCAM2",
        "event_type": "anpr",
        "vehicle_number": "MH12QQ4321",
        "vehicle_type": "car",
        "confidence": 0.9,
        "bounding_box": {"x": 1, "y": 1, "w": 2, "h": 2},
    }
    resp = client.post("/api/v1/events/ingest", json=payload, headers=admin_headers)
    assert resp.status_code == 201

    resp = client.get("/api/v1/alerts?camera_id=TCAM2", headers=admin_headers)
    assert resp.status_code == 200
    assert all(a["matched_identifier"] != "MH12QQ4321" for a in resp.json())


def test_ingest_event_matching_watchlist_creates_alert(client, admin_headers):
    payload = {
        "camera_id": "TCAM2",
        "event_type": "anpr",
        "vehicle_number": "GJ09ZZ0007",
        "vehicle_type": "truck",
        "confidence": 0.93,
        "bounding_box": {"x": 5, "y": 5, "w": 40, "h": 20},
    }
    resp = client.post("/api/v1/events/ingest", json=payload, headers=admin_headers)
    assert resp.status_code == 201

    resp = client.get("/api/v1/alerts?camera_id=TCAM2", headers=admin_headers)
    assert resp.status_code == 200
    alerts = resp.json()
    assert any(a["matched_identifier"] == "GJ09ZZ0007" and a["severity"] == "critical" for a in alerts)


def test_duplicate_event_within_window_is_deduplicated(client, admin_headers):
    payload = {
        "camera_id": "TCAM2",
        "event_type": "anpr",
        "vehicle_number": "GJ09ZZ0007",
        "vehicle_type": "truck",
        "confidence": 0.5,
        "bounding_box": {},
    }
    resp1 = client.post("/api/v1/events/ingest", json=payload, headers=admin_headers)
    resp2 = client.post("/api/v1/events/ingest", json=payload, headers=admin_headers)
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    # Same dedup bucket -> the same underlying event is returned, not a new one.
    assert resp1.json()["id"] == resp2.json()["id"]


def test_ingest_unknown_camera_rejected(client, admin_headers):
    payload = {
        "camera_id": "DOES-NOT-EXIST",
        "event_type": "anpr",
        "vehicle_number": "GJ01XX0000",
        "confidence": 0.8,
        "bounding_box": {},
    }
    resp = client.post("/api/v1/events/ingest", json=payload, headers=admin_headers)
    assert resp.status_code == 422


def test_alert_acknowledge_workflow(client, admin_headers):
    resp = client.get("/api/v1/alerts?camera_id=TCAM2", headers=admin_headers)
    alert_id = resp.json()[0]["id"]

    resp = client.patch(
        f"/api/v1/alerts/{alert_id}", json={"status": "acknowledged"}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"

    resp = client.patch(
        f"/api/v1/alerts/{alert_id}",
        json={"status": "resolved", "notes": "Verified false positive plate read"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
