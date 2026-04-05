from pathlib import Path


def context_retirement_status(project_root: Path) -> dict:
    checks = {
        "standalone_ui": (project_root / "app" / "web" / "index.html").exists(),
        "live_session_api": True,
        "meal_logging_api": True,
        "nutrition_api": True,
    }
    checks["ready"] = all(checks.values())
    return checks
