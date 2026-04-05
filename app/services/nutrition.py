from app.contracts.nutrition import DailyStats, Meal


def calculate_daily_stats(meals: list[Meal]) -> DailyStats:
    totals = DailyStats(calories=0, protein=0, carbs=0, fat=0, fiber=0)
    for meal in meals:
        totals.calories += meal.calories
        totals.protein += meal.protein
        totals.carbs += meal.carbs
        totals.fat += meal.fat
        totals.fiber += meal.fiber
    return totals

