from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_meal_and_list_meals() -> None:
    payload = {
        "name": "Chicken bowl",
        "calories": 550,
        "protein": 42,
        "carbs": 40,
        "fat": 20,
        "fiber": 7,
        "timestamp": "2026-04-05T12:10:00Z",
        "type": "lunch",
    }
    create = client.post("/v1/meals", json=payload)
    assert create.status_code == 200
    entry = create.json()
    assert entry["name"] == "Chicken bowl"
    assert "id" in entry

    listed = client.get("/v1/meals")
    assert listed.status_code == 200
    items = listed.json()
    assert any(item["id"] == entry["id"] for item in items)


def test_list_meals_can_filter_by_date_prefix() -> None:
    client.post(
        "/v1/meals",
        json={
            "name": "Breakfast meal",
            "calories": 300,
            "protein": 20,
            "carbs": 25,
            "fat": 10,
            "fiber": 4,
            "timestamp": "2026-04-06T08:00:00Z",
            "type": "breakfast",
        },
    )
    filtered = client.get("/v1/meals?date=2026-04-06")
    assert filtered.status_code == 200
    items = filtered.json()
    assert all(item["timestamp"].startswith("2026-04-06") for item in items)
