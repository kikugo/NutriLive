from typing import Literal

from pydantic import BaseModel


class UserProfile(BaseModel):
    display_name: str
    calorie_goal: int
    protein_goal: int
    carbs_goal: int
    fat_goal: int
    fiber_goal: int


class Meal(BaseModel):
    name: str
    calories: int
    protein: int
    carbs: int
    fat: int
    fiber: int
    timestamp: str
    type: Literal["breakfast", "lunch", "dinner", "snack"]


class DailyStats(BaseModel):
    calories: int
    protein: int
    carbs: int
    fat: int
    fiber: int
