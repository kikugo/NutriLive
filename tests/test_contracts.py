import pytest
from pydantic import ValidationError

from app.contracts.nutrition import Meal


def test_meal_contract_accepts_expected_shape() -> None:
    meal = Meal(
        name="Chicken salad",
        calories=420,
        protein=35,
        carbs=20,
        fat=18,
        fiber=7,
        timestamp="2026-04-05T12:00:00Z",
        type="lunch",
    )
    assert meal.type == "lunch"


def test_meal_contract_rejects_negative_values() -> None:
    with pytest.raises(ValidationError):
        Meal(
            name="Invalid meal",
            calories=-10,
            protein=20,
            carbs=15,
            fat=6,
            fiber=3,
            timestamp="2026-04-05T12:00:00Z",
            type="lunch",
        )
