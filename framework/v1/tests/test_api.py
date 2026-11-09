from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def test_health_and_rules():
    assert client.get("/api/health").json()["status"] == "ok"
    rules = client.get("/api/rules").json()
    assert len(rules) == 54


def test_compare():
    r = client.post("/api/compare", json={
        "idea1": {"what": "Window composed of heat-sensitive material", "how": "indicates the exit path"},
        "idea2": {"what": "Window made of heat-sensitive material", "how": "shows the exit path"}})
    assert r.status_code == 200
    assert r.json()["relationship"] == "duplicate"


def test_compare_with_options():
    r = client.post("/api/compare", json={
        "idea1": {"what": "window", "how": "indicates the exit path"},
        "idea2": {"what": "smoke", "how": "shows the escape route"},
        "options": {"enabled": ["structure", "linguistic"], "content": 0.9}})
    assert r.status_code == 200
    assert r.json()["relationship"]


def test_missing_what_is_rejected():
    r = client.post("/api/compare", json={"idea1": {"what": ""}, "idea2": {"what": "x"}})
    assert r.status_code == 422


def test_frontend_served():
    assert "idearel" in client.get("/").text


def test_segment_endpoint():
    d = client.post("/api/segment", json={"text": "Rescue floor, that lights up to show the exit path in case of fire"}).json()
    assert d["what"].lower().startswith("rescue floor") and "lights up" in d["how"] and "case of fire" in d["when"]
