"""API contract tests: machines, predictions, alerts, maintenance."""

from __future__ import annotations


def _create_milling_machine(client, quality_type="L"):
    r = client.post(
        "/machines", json={"name": "Machine #1", "machine_type": "milling", "quality_type": quality_type}
    )
    assert r.status_code == 201
    return r.json()["id"]


def _create_turbofan_machine(client):
    r = client.post("/machines", json={"name": "Engine #1", "machine_type": "turbofan"})
    assert r.status_code == 201
    return r.json()["id"]


CRITICAL_MILLING_READING = {
    "air_temp_k": 302.5,
    "process_temp_k": 312.0,
    "rotational_speed_rpm": 1350,
    "torque_nm": 62.0,
    "tool_wear_min": 220,
    "type": "L",
}


def test_machine_crud_and_404(client):
    mid = _create_milling_machine(client)
    assert client.get("/machines").json()[0]["id"] == mid
    assert client.get(f"/machines/{mid}").status_code == 200
    assert client.get("/machines/999").status_code == 404


def test_score_milling_reading_creates_prediction(client):
    mid = _create_milling_machine(client)
    r = client.post(f"/machines/{mid}/score", json=CRITICAL_MILLING_READING)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "critical"
    assert body["failure_probability"] > 0.5
    assert body["rul_cycles"] is None


def test_score_unknown_machine_404s(client):
    r = client.post("/machines/999/score", json=CRITICAL_MILLING_READING)
    assert r.status_code == 404


def test_score_invalid_reading_422s(client):
    mid = _create_milling_machine(client)
    r = client.post(f"/machines/{mid}/score", json={"air_temp_k": "not a number"})
    assert r.status_code == 422


def test_critical_reading_creates_alerts_and_dedups(client):
    mid = _create_milling_machine(client)
    client.post(f"/machines/{mid}/score", json=CRITICAL_MILLING_READING)
    client.post(f"/machines/{mid}/score", json=CRITICAL_MILLING_READING)  # identical, again

    alerts = client.get("/alerts").json()
    kinds = sorted(a["kind"] for a in alerts)
    # one alert per kind that fired, not one per reading
    assert kinds == sorted(set(kinds))
    assert len(alerts) >= 1

    alert_id = alerts[0]["id"]
    ack = client.post(f"/alerts/{alert_id}/acknowledge")
    assert ack.json()["acknowledged"] is True

    client.post(f"/machines/{mid}/score", json=CRITICAL_MILLING_READING)
    alerts_after = client.get("/alerts").json()
    assert len(alerts_after) == len(alerts) + 1  # only the acknowledged kind re-fires


def test_turbofan_scoring_over_multiple_cycles(client):
    from ml import cmapss as C

    tid = _create_turbofan_machine(client)
    _, test, rul_truth = C.load_subset("FD001")
    g = test[test["unit"] == 1].sort_values("cycle")

    last = None
    for _, row in g.iterrows():
        body = {
            "cycle": int(row["cycle"]),
            "op_setting_1": row["op_setting_1"],
            "op_setting_2": row["op_setting_2"],
            "op_setting_3": row["op_setting_3"],
            "sensors": {f"sensor_{i}": row[f"sensor_{i}"] for i in range(1, 22)},
        }
        r = client.post(f"/machines/{tid}/score", json=body)
        assert r.status_code == 201
        last = r.json()

    assert last["rul_cycles"] is not None
    assert abs(last["rul_cycles"] - float(rul_truth[0])) < 30
    assert len(client.get(f"/machines/{tid}/readings").json()) == len(g)


def test_maintenance_crud(client):
    mid = _create_milling_machine(client)
    r = client.post(
        "/maintenance",
        json={
            "machine_id": mid,
            "maintenance_date": "2026-06-01",
            "issue": "Excess tool wear",
            "action_taken": "Replaced tool",
            "technician": "A. Rai",
            "cost": 120.5,
        },
    )
    assert r.status_code == 201
    record_id = r.json()["id"]

    assert len(client.get("/maintenance").json()) == 1
    assert len(client.get(f"/maintenance?machine_id={mid}").json()) == 1
    assert len(client.get("/maintenance?machine_id=999").json()) == 0

    assert client.delete(f"/maintenance/{record_id}").status_code == 204
    assert client.get("/maintenance").json() == []
    assert client.delete(f"/maintenance/{record_id}").status_code == 404
