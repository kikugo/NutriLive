"""Look up authoritative macros from USDA FoodData Central.

Gemini parses the spoken meal into a food name plus an estimated portion in
grams. This layer takes that (name, grams) and returns database-backed macros
scaled to the portion, so the numbers stop being a pure LLM guess.

Modes (``NUTRITION_LOOKUP_MODE``):
- ``off`` (default): no lookup; the upstream estimate is used as-is.
- ``usda``: query FoodData Central (requires ``USDA_API_KEY``).

A lookup only overrides the estimate when it has a portion size and a match;
otherwise the estimate is kept and tagged ``source="estimate"``.
"""

from dataclasses import dataclass

from app.config import get_settings

# USDA nutrient numbers -> our macro field names.
_NUTRIENT_NUMBERS = {
    "208": "calories",  # Energy (kcal)
    "203": "protein",
    "204": "fat",  # Total lipid
    "205": "carbs",  # Carbohydrate, by difference
    "291": "fiber",  # Fiber, total dietary
}


@dataclass
class MacroResult:
    calories: int
    protein: int
    carbs: int
    fat: int
    fiber: int
    source: str = "usda"
    matched_name: str | None = None


def parse_food_macros(food: dict, grams: float) -> MacroResult | None:
    """Turn one FoodData Central food record (per-100g) into scaled macros."""
    per_100g: dict[str, float] = {}
    for nutrient in food.get("foodNutrients") or []:
        number = str(
            nutrient.get("nutrientNumber")
            or (nutrient.get("nutrient") or {}).get("number")
            or ""
        )
        field = _NUTRIENT_NUMBERS.get(number)
        if not field:
            continue
        # Energy is reported in both KCAL and KJ; keep only kcal.
        unit = (nutrient.get("unitName") or "").upper()
        if number == "208" and unit and unit != "KCAL":
            continue
        value = nutrient.get("value")
        if value is None:
            value = nutrient.get("amount")
        if value is not None:
            per_100g[field] = float(value)

    if "calories" not in per_100g:
        return None

    factor = grams / 100.0
    return MacroResult(
        calories=round(per_100g.get("calories", 0) * factor),
        protein=round(per_100g.get("protein", 0) * factor),
        carbs=round(per_100g.get("carbs", 0) * factor),
        fat=round(per_100g.get("fat", 0) * factor),
        fiber=round(per_100g.get("fiber", 0) * factor),
        source="usda",
        matched_name=food.get("description"),
    )


class NutritionLookup:
    """No-op lookup: never overrides the upstream estimate."""

    async def lookup(self, name: str | None, grams: float | None) -> MacroResult | None:
        return None


class UsdaNutritionLookup(NutritionLookup):
    SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

    async def lookup(self, name: str | None, grams: float | None) -> MacroResult | None:
        settings = get_settings()
        if not name or not settings.usda_api_key or not grams or grams <= 0:
            return None

        import httpx

        params = {
            "api_key": settings.usda_api_key,
            "query": name,
            "pageSize": 1,
            "dataType": "Foundation,SR Legacy",
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.SEARCH_URL, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return None

        foods = data.get("foods") or []
        if not foods:
            return None
        return parse_food_macros(foods[0], grams)


def create_nutrition_lookup() -> NutritionLookup:
    if get_settings().nutrition_lookup_mode.lower() == "usda":
        return UsdaNutritionLookup()
    return NutritionLookup()
