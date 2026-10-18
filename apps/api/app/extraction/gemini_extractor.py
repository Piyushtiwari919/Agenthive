import json
import httpx

from app.config import get_settings
from app.extraction.base import ExtractionPayload


class GeminiExtractor:
    """
    Optional hosted Gemini API extractor adapter (C-03).
    Used only when EXTRACTION_PROVIDER=gemini and GEMINI_API_KEY is configured.
    """

    provider_name: str = "gemini"

    def extract(self, content: str) -> ExtractionPayload:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        )
        prompt = (
            "Extract technical entities, facts, and repeatable procedures from the episode below. "
            "Return strict JSON matching keys: entities (list of {name, entity_type, aliases}), "
            "facts (list of {subject_name, subject_type, predicate, object_value, confidence}), "
            "procedures (list of {name, trigger_text, steps}).\n\nEpisode:\n" + content
        )
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
            return ExtractionPayload.model_validate(parsed)
        