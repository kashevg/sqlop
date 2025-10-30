"""Configuration management for SQLOp application."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class DatabaseConfig:
    """Database connection configuration."""

    host: str
    port: int
    name: str
    user: str
    password: str


@dataclass
class GeminiConfig:
    """Gemini API configuration."""

    model: str
    temperature: float
    gcp_project_id: Optional[str] = None
    gcp_location: Optional[str] = None
    api_key: Optional[str] = None

    def is_vertex_ai(self) -> bool:
        """Check if using Vertex AI (vs API key)."""
        return self.gcp_project_id is not None


@dataclass
class AppConfig:
    """Main application configuration."""

    database: DatabaseConfig
    gemini: GeminiConfig
    data_dir: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables."""
        database = DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            name=os.getenv("DB_NAME", "sqlop"),
            user=os.getenv("DB_USER", "sqlop_user"),
            password=os.getenv("DB_PASSWORD", "sqlop_password"),
        )

        gemini = GeminiConfig(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
            temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
            gcp_project_id=os.getenv("GCP_PROJECT_ID"),
            gcp_location=os.getenv("GCP_LOCATION", "us-central1"),
            api_key=os.getenv("GOOGLE_API_KEY"),
        )

        # Validate Gemini config
        if not gemini.is_vertex_ai() and not gemini.api_key:
            raise ValueError(
                "Either GCP_PROJECT_ID or GOOGLE_API_KEY must be set in environment"
            )

        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
        )
        os.makedirs(data_dir, exist_ok=True)

        return cls(database=database, gemini=gemini, data_dir=data_dir)
