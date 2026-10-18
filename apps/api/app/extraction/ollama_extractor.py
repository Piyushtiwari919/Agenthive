import json
import httpx

from app.config import get_settings
from app.extraction.base import ExtractionPayload


class OllamaExtractor:
    """
    Optional local Ollama model adapter (C-03).
    """

    provider_name: str = "ollama"

    def extract(self, content: str) -> ExtractionPayload:
        settings = get_settings()
        url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
        prompt = (
            "Extract entities, facts, and procedures as JSON with keys 'entities', 'facts', 'procedures'.\n"
            f"Episode: {content}"
        )
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                url,
                json={"model": settings.ollama_model, "prompt": prompt, "stream": False, "format": "json"},
            )
            resp.raise_for_status()
            raw_json = resp.json().get("response", "{}")
            return ExtractionPayload.model_validate(json.loads(raw_json))