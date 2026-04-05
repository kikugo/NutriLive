from typing import Literal

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    display_name: str
    calorie_goal: int = Field(ge=0)
    protein_goal: int = Field(ge=0)
    carbs_goal: int = Field(ge=0)
    fat_goal: int = Field(ge=0)
    fiber_goal: int = Field(ge=0)


class Meal(BaseModel):
    name: str
    calories: int = Field(ge=0)
    protein: int = Field(ge=0)
    carbs: int = Field(ge=0)
    fat: int = Field(ge=0)
    fiber: int = Field(ge=0)
    timestamp: str
    type: Literal["breakfast", "lunch", "dinner", "snack"]


class DailyStats(BaseModel):
    calories: int = Field(ge=0)
    protein: int = Field(ge=0)
    carbs: int = Field(ge=0)
    fat: int = Field(ge=0)
    fiber: int = Field(ge=0)
