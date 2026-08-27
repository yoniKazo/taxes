"""מטלה 4 -- בדיקות ל-endpoints החינמיים של /agent-lab (0 קריאות LLM): tools,
tasks, configs CRUD, matrix (read-only), cost. אותו דפוס כמו test_rag_backend.py --
TestClient, בלי מפתחות API נחוצים."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402

client = TestClient(app)


def test_list_tools_returns_three_tools_with_failure_contract_in_description():
    response = client.get("/agent-lab/tools")
    assert response.status_code == 200
    tools = response.json()["tools"]
    names = {t["name"] for t in tools}
    assert names == {"search_tax_corpus", "calculator", "calculate_tax_refund"}
    for tool in tools:
        assert "ERROR" in tool["description"] or "NO_RESULTS" in tool["description"]


def test_list_tasks_matches_the_required_composition():
    response = client.get("/agent-lab/tasks")
    assert response.status_code == 200
    tasks = response.json()["tasks"]
    assert len(tasks) == 24
    by_type = {}
    for task in tasks:
        by_type[task["type"]] = by_type.get(task["type"], 0) + 1
    assert by_type["multi_hop"] >= 6
    assert by_type["no_tool"] == 3
    assert by_type["unanswerable"] == 3
    assert by_type["tool_fails"] == 2


def test_canonical_config_always_present_and_undeletable():
    response = client.get("/agent-lab/configs")
    assert response.status_code == 200
    configs = response.json()["configs"]
    assert any(c["id"] == "canonical" for c in configs)

    delete_response = client.delete("/agent-lab/configs/canonical")
    assert delete_response.status_code == 400


def test_add_and_delete_config_roundtrip():
    add_response = client.post("/agent-lab/configs", json={
        "name": "בדיקה", "model": "claude-haiku-4-5",
        "enabled_tools": ["calculator"], "system_prompt": None,
    })
    assert add_response.status_code == 200
    config_id = add_response.json()["id"]

    listed = client.get("/agent-lab/configs").json()["configs"]
    assert any(c["id"] == config_id for c in listed)

    delete_response = client.delete(f"/agent-lab/configs/{config_id}")
    assert delete_response.status_code == 204

    listed_after = client.get("/agent-lab/configs").json()["configs"]
    assert not any(c["id"] == config_id for c in listed_after)


def test_delete_unknown_config_is_404():
    response = client.delete("/agent-lab/configs/does-not-exist")
    assert response.status_code == 404


def test_matrix_endpoint_never_errors_even_before_a_run_exists():
    response = client.get("/agent-lab/matrix")
    assert response.status_code == 200
    assert "available" in response.json()


def test_cost_endpoint_returns_zero_before_any_run():
    response = client.get("/agent-lab/cost")
    assert response.status_code == 200
    body = response.json()
    assert "total_usd" in body
    assert body["total_usd"] >= 0
