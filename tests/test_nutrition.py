from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_daily_stats_endpoint_aggregates_meals() -> None:
    payload = [
        {
            "name": "Chicken bowl",
            "calories": 500,
            "protein": 40,
            "carbs": 35,
            "fat": 20,
            "fiber": 8,
            "timestamp": "2026-04-05T12:00:00Z",
            "type": "lunch",
        },
        {
            "name": "Protein shake",
            "calories": 220,
            "protein": 30,
            "carbs": 12,
            "fat": 4,
            "fiber": 2,
            "timestamp": "2026-04-05T16:00:00Z",
            "type": "snack",
        },
    ]

    response = client.post("/v1/nutrition/daily-stats", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["calories"] == 720
    assert body["protein"] == 70
    assert body["carbs"] == 47
    assert body["fat"] == 24
    assert body["fiber"] == 10


def test_daily_stats_endpoint_rejects_invalid_meal_payload() -> None:
    payload = [
        {
            "name": "Invalid meal",
            "calories": -1,
            "protein": 10,
            "carbs": 10,
            "fat": 10,
            "fiber": 1,
            "timestamp": "2026-04-05T12:00:00Z",
            "type": "lunch",
        }
    ]
    response = client.post("/v1/nutrition/daily-stats", json=payload)
    assert response.status_code == 422
