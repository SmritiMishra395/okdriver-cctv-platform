def test_create_camera_requires_admin(client, operator_headers):
    payload = {
        "id": "TCAM1",
        "name": "Test Camera",
        "department": "Test Dept",
        "latitude": 23.0,
        "longitude": 72.5,
        "source_protocol": "simulator",
        "stream_ref": "simulator:TCAM1:Test",
    }
    resp = client.post("/api/v1/cameras", json=payload, headers=operator_headers)
    assert resp.status_code == 403


def test_create_and_list_camera(client, admin_headers):
    payload = {
        "id": "TCAM1",
        "name": "Test Junction Camera",
        "department": "Test Traffic Dept",
        "zone": "Zone-Test",
        "latitude": 23.05,
        "longitude": 72.58,
        "source_protocol": "simulator",
        "stream_ref": "simulator:TCAM1:Test Junction",
    }
    resp = client.post("/api/v1/cameras", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["id"] == "TCAM1"
    # Stream credentials must never come back in plain text.
    assert body["stream_ref_masked"] == "simulator:TCAM1:Test Junction"

    resp = client.get("/api/v1/cameras", headers=admin_headers)
    assert resp.status_code == 200
    assert any(c["id"] == "TCAM1" for c in resp.json())


def test_duplicate_camera_id_rejected(client, admin_headers):
    payload = {
        "id": "TCAM1",
        "name": "Duplicate",
        "department": "Test Traffic Dept",
        "latitude": 23.05,
        "longitude": 72.58,
        "source_protocol": "simulator",
        "stream_ref": "simulator:TCAM1:Test",
    }
    resp = client.post("/api/v1/cameras", json=payload, headers=admin_headers)
    assert resp.status_code == 409


def test_search_and_filter(client, admin_headers):
    resp = client.get("/api/v1/cameras?q=Junction", headers=admin_headers)
    assert resp.status_code == 200
    assert all("Junction" in c["name"] or "junction" in c["name"].lower() for c in resp.json())


def test_disable_and_enable_camera(client, admin_headers):
    resp = client.post("/api/v1/cameras/TCAM1/disable", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    resp = client.post("/api/v1/cameras/TCAM1/enable", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


def test_camera_audit_history_records_actions(client, admin_headers):
    resp = client.get("/api/v1/cameras/TCAM1/audit", headers=admin_headers)
    assert resp.status_code == 200
    actions = [entry["action"] for entry in resp.json()]
    assert "camera.create" in actions
    assert "camera.disable" in actions
    assert "camera.enable" in actions
