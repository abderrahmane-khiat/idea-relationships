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


def test_compare_with_oracle_and_options():
    r = client.post("/api/compare", json={
        "idea1": {"what": "", "how": "", "oracle_what": {"type": "single_term", "text": "window"},
                  "oracle_how": {"type": "single_term", "text": "exit path"}},
        "idea2": {"what": "", "how": "", "oracle_what": {"type": "single_term", "text": "smoke"},
                  "oracle_how": {"type": "single_term", "text": "escape route"}},
        "options": {"enabled": ["structure", "linguistic"], "content": 0.9}})
    assert r.status_code == 200
    d = r.json()
    assert d["elements"]["idea1"]["WHAT"]["source"] == "oracle"


def test_missing_what_is_rejected():
    r = client.post("/api/compare", json={"idea1": {"what": ""}, "idea2": {"what": "x"}})
    assert r.status_code == 422


def test_frontend_served():
    assert "idearel" in client.get("/").text


def test_compare_v2_and_rules_v2():
    r = client.post("/api/compare", json={
        "idea1": {"what": "waterproof carpet", "how": "that absorbs water"},
        "idea2": {"what": "", "how": ""}, "options": {"rules_version": "v2"}})
    assert r.status_code == 422
    r = client.post("/api/compare", json={
        "idea1": {"what": "waterproof carpet", "how": "that absorbs water"},
        "idea2": {"what": "waterproof floor", "how": ""}, "options": {"rules_version": "v2"}})
    assert r.json()["relationship"] == "unknown" and r.json()["rule_id"] == "U02"
    assert len(client.get("/api/rules?version=v2").json()) == 16


def test_segment_endpoint():
    d = client.post("/api/segment", json={"text": "Rescue floor, that lights up to show the exit path in case of fire"}).json()
    assert d["what"].lower().startswith("rescue floor") and "lights up" in d["how"] and "case of fire" in d["when"]
