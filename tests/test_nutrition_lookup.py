from app.config import get_settings
from app.services.live_bridge import LiveBridge
from app.services.nutrition_lookup import (
    MacroResult,
    NutritionLookup,
    UsdaNutritionLookup,
    create_nutrition_lookup,
    parse_food_macros,
)
from app.services.upstream import UpstreamClient

# A trimmed FoodData Central "foods/search" record, values per 100g.
_FDC_FOOD = {
    "description": "Eggs, scrambled",
    "foodNutrients": [
        {"nutrientNumber": "208", "unitName": "kJ", "value": 623},
        {"nutrientNumber": "208", "unitName": "KCAL", "value": 149},
        {"nutrientNumber": "203", "unitName": "G", "value": 10.1},
        {"nutrientNumber": "204", "unitName": "G", "value": 10.9},
        {"nutrientNumber": "205", "unitName": "G", "value": 1.6},
        {"nutrientNumber": "291", "unitName": "G", "value": 0.0},
    ],
}


def test_parse_food_macros_scales_by_portion_and_prefers_kcal() -> None:
    result = parse_food_macros(_FDC_FOOD, grams=200)
    assert result is not None
    # per-100g x 2.0, with energy taken from the KCAL row not the kJ row.
    assert result.calories == 298
    assert result.protein == 20
    assert result.fat == 22
    assert result.carbs == 3
    assert result.fiber == 0
    assert result.source == "usda"
    assert result.matched_name == "Eggs, scrambled"


def test_parse_food_macros_returns_none_without_energy() -> None:
    assert parse_food_macros({"foodNutrients": [{"nutrientNumber": "203", "value": 5}]}, 100) is None


def test_create_nutrition_lookup_selects_mode(monkeypatch) -> None:
    monkeypatch.setenv("NUTRITION_LOOKUP_MODE", "usda")
    get_settings.cache_clear()
    assert isinstance(create_nutrition_lookup(), UsdaNutritionLookup)

    monkeypatch.setenv("NUTRITION_LOOKUP_MODE", "off")
    get_settings.cache_clear()
    assert type(create_nutrition_lookup()) is NutritionLookup


class _FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


class _FixedLookup(NutritionLookup):
    def __init__(self, result: MacroResult | None) -> None:
        self._result = result

    async def lookup(self, name, grams) -> MacroResult | None:
        return self._result


def _bridge(lookup: NutritionLookup) -> LiveBridge:
    return LiveBridge(upstream_client=UpstreamClient(), nutrition_lookup=lookup)


async def test_tool_call_macros_overridden_by_lookup() -> None:
    lookup = _FixedLookup(
        MacroResult(calories=298, protein=20, carbs=3, fat=22, fiber=0, matched_name="Eggs, scrambled")
    )
    bridge = _bridge(lookup)
    ws = _FakeWebSocket()

    await bridge._handle_upstream_event(
        ws,
        {
            "type": "tool_call",
            "name": "prepare_meal_log",
            "args": {"name": "eggs", "grams": 200, "calories": 999, "protein": 1,
                     "carbs": 1, "fat": 1, "fiber": 1, "type": "breakfast"},
        },
    )

    args = ws.sent[0]["args"]
    assert args["calories"] == 298
    assert args["protein"] == 20
    assert args["source"] == "usda"
    assert args["matched_name"] == "Eggs, scrambled"


async def test_tool_call_keeps_estimate_when_no_match() -> None:
    bridge = _bridge(_FixedLookup(None))
    ws = _FakeWebSocket()

    await bridge._handle_upstream_event(
        ws,
        {
            "type": "tool_call",
            "name": "prepare_meal_log",
            "args": {"name": "eggs", "calories": 450, "type": "lunch"},
        },
    )

    args = ws.sent[0]["args"]
    assert args["calories"] == 450
    assert args["source"] == "estimate"


async def test_usda_lookup_calls_api_and_parses_response(monkeypatch) -> None:
    monkeypatch.setenv("USDA_API_KEY", "test-key")
    get_settings.cache_clear()
    captured: dict = {}

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"foods": [_FDC_FOOD]}

    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "_FakeClient":
            return self

        async def __aexit__(self, *args) -> bool:
            return False

        async def get(self, url, params=None) -> _FakeResponse:
            captured["url"] = url
            captured["params"] = params
            return _FakeResponse()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)

    result = await UsdaNutritionLookup().lookup("scrambled eggs", grams=200)
    assert result is not None
    assert result.calories == 298
    assert result.source == "usda"
    assert captured["params"]["query"] == "scrambled eggs"
    assert captured["params"]["api_key"] == "test-key"


async def test_usda_lookup_skips_without_key_or_portion(monkeypatch) -> None:
    monkeypatch.delenv("USDA_API_KEY", raising=False)
    get_settings.cache_clear()
    assert await UsdaNutritionLookup().lookup("eggs", grams=200) is None

    monkeypatch.setenv("USDA_API_KEY", "test-key")
    get_settings.cache_clear()
    assert await UsdaNutritionLookup().lookup("eggs", grams=None) is None


async def test_non_tool_events_pass_through_untouched() -> None:
    bridge = _bridge(_FixedLookup(None))
    ws = _FakeWebSocket()
    event = {"type": "model_transcript", "text": "hello", "finished": True}

    await bridge._handle_upstream_event(ws, event)

    assert ws.sent[0] == event
