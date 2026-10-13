"""Lists the models each provider offers and flags configured models that no longer exist.

Run: docker compose run --rm --no-deps backend python -m scripts.list_models
"""

import os
import sys

import httpx

from app.settings import load_models_config


def groq() -> list[str]:
    response = httpx.get(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
    )
    response.raise_for_status()
    return [model["id"] for model in response.json()["data"]]


def gemini() -> list[str]:
    response = httpx.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        params={"pageSize": 1000},
    )
    response.raise_for_status()
    return [
        model["name"].removeprefix("models/")
        for model in response.json()["models"]
        if "generateContent" in model.get("supportedGenerationMethods", [])
    ]


def openrouter_free() -> list[str]:
    response = httpx.get("https://openrouter.ai/api/v1/models")
    response.raise_for_status()
    return [model["id"] for model in response.json()["data"] if model["id"].endswith(":free")]


PROVIDERS = {"groq": groq, "gemini": gemini, "openrouter": openrouter_free}


def main() -> int:
    available: dict[str, set[str]] = {}
    for provider, fetch in PROVIDERS.items():
        try:
            ids = sorted(fetch())
        except (KeyError, httpx.HTTPError) as error:
            print(f"== {provider}: failed ({type(error).__name__}: {error})")
            continue
        available[provider] = set(ids)
        print(f"== {provider} ({len(ids)})")
        for model_id in ids:
            print(f"   {model_id}")

    missing = []
    for role, models in load_models_config().roles.items():
        for model in models:
            provider, model_id = model.split("/", 1)
            if provider in available and model_id not in available[provider]:
                missing.append(f"{role}: {model}")
    print("== configured models not offered:", ", ".join(missing) or "none")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
