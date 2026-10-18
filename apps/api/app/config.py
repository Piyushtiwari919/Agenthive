import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parent
_REPO_ROOT = _API_ROOT.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(_REPO_ROOT / ".env"),
            str(_API_ROOT / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    agenthive_env: Literal["demo", "production", "test"] = Field(default="demo", alias="AGENTHIVE_ENV")
    agenthive_host: str = Field(default="0.0.0.0", alias="AGENTHIVE_HOST")
    agenthive_port: int = Field(default=8000, alias="AGENTHIVE_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # FalkorDB Primary Database Configuration (C-01)
    falkordb_host: str = Field(default="localhost", alias="FALKORDB_HOST")
    falkordb_port: int = Field(default=6379, alias="FALKORDB_PORT")
    falkordb_username: str = Field(default="", alias="FALKORDB_USERNAME")
    falkordb_password: str = Field(default="", alias="FALKORDB_PASSWORD")
    falkordb_ssl: bool = Field(default=False, alias="FALKORDB_SSL")
    falkordb_control_graph: str = Field(default="ah_control", alias="FALKORDB_CONTROL_GRAPH")

    # Extraction Configuration (C-03, NFR-004)
    extraction_provider: Literal["deterministic", "ollama", "gemini"] = Field(
        default="deterministic", alias="EXTRACTION_PROVIDER"
    )
    extraction_worker_enabled: bool = Field(default=True, alias="EXTRACTION_WORKER_ENABLED")
    extraction_poll_interval_seconds: float = Field(
        default=1.5, alias="EXTRACTION_POLL_INTERVAL_SECONDS"
    )
    extraction_simulate_outage: bool = Field(default=False, alias="EXTRACTION_SIMULATE_OUTAGE")
    extraction_max_attempts: int = Field(default=5, alias="EXTRACTION_MAX_ATTEMPTS")

    # Optional External Providers
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", alias="OLLAMA_MODEL")

    # Security & Tenancy
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        alias="CORS_ORIGINS",
    )
    demo_default_tenant: str = Field(default="alpha-eng", alias="DEMO_DEFAULT_TENANT")
    production_tenant_tokens_json: str = Field(
        default="{}", alias="PRODUCTION_TENANT_TOKENS_JSON"
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def production_tenant_tokens(self) -> Dict[str, str]:
        try:
            parsed = json.loads(self.production_tenant_tokens_json or "{}")
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
            return {}
        except json.JSONDecodeError:
            return {}

    @field_validator("falkordb_control_graph")
    @classmethod
    def validate_control_graph(cls, v: str) -> str:
        clean = v.strip()
        if not clean or not clean.replace("_", "").isalnum():
            raise ValueError("FALKORDB_CONTROL_GRAPH must be a safe alphanumeric/underscore identifier.")
        return clean

    def validate_startup_security(self) -> None:
        if self.agenthive_env == "production" and not self.production_tenant_tokens:
            raise RuntimeError(
                "Refusing unsafe production startup: PRODUCTION_TENANT_TOKENS_JSON must configure "
                "tenant-bound authentication tokens when AGENTHIVE_ENV=production."
            )


@lru_cache()
def get_settings() -> Settings:
    return Settings()