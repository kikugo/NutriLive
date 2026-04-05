from app.contracts.nutrition import DailyStats, Meal, NutritionGoals


def calculate_daily_stats(meals: list[Meal]) -> DailyStats:
    totals = DailyStats(calories=0, protein=0, carbs=0, fat=0, fiber=0)
    for meal in meals:
        totals.calories += meal.calories
        totals.protein += meal.protein
        totals.carbs += meal.carbs
        totals.fat += meal.fat
        totals.fiber += meal.fiber
    return totals


def calculate_progress(meals: list[Meal], goals: NutritionGoals) -> dict:
    consumed = calculate_daily_stats(meals)
    payload: dict[str, dict] = {}

    for key in ("calories", "protein", "carbs", "fat", "fiber"):
        consumed_value = getattr(consumed, key)
        goal_value = getattr(goals, key)
        remaining = max(goal_value - consumed_value, 0)
        percentage = 0 if goal_value == 0 else round((consumed_value / goal_value) * 100, 2)
        payload[key] = {
            "consumed": consumed_value,
            "goal": goal_value,
            "remaining": remaining,
            "percentage": percentage,
        }

    return payload
