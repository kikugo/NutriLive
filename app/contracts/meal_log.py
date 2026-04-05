from pydantic import BaseModel, Field


class MealLogCreate(BaseModel):
    name: str
    calories: int = Field(ge=0)
    protein: int = Field(ge=0)
    carbs: int = Field(ge=0)
    fat: int = Field(ge=0)
    fiber: int = Field(ge=0)
    timestamp: str
    type: str


class MealLogEntry(MealLogCreate):
    id: str
