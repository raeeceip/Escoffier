"""
Configuration management using Pydantic Settings for robust validation and environment handling.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
import os
from pathlib import Path


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(
        default="sqlite:///./data/escoffier.db",
        description="Database URL (SQLite, PostgreSQL, etc.)"
    )
    echo: bool = Field(
        default=False,
        description="Enable SQLAlchemy query logging"
    )
    pool_size: int = Field(
        default=10,
        description="Connection pool size"
    )


class OpenAIConfig(BaseSettings):
    """OpenAI API configuration."""
    
    api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    model: str = Field(
        default="gpt-4-turbo-preview",
        description="Default OpenAI model"
    )
    base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL"
    )
    enabled: bool = Field(
        default=False,
        description="Enable OpenAI provider"
    )
    max_tokens: int = Field(
        default=1000,
        description="Default max tokens for responses"
    )
    temperature: float = Field(
        default=0.7,
        description="Default temperature for responses"
    )

    class Config:
        env_prefix = "OPENAI_"


class AnthropicConfig(BaseSettings):
    """Anthropic Claude API configuration."""
    
    api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    model: str = Field(
        default="claude-3-sonnet-20240229",
        description="Default Anthropic model"
    )
    base_url: str = Field(
        default="https://api.anthropic.com",
        description="Anthropic API base URL"
    )
    enabled: bool = Field(
        default=False,
        description="Enable Anthropic provider"
    )
    max_tokens: int = Field(
        default=1000,
        description="Default max tokens for responses"
    )
    temperature: float = Field(
        default=0.7,
        description="Default temperature for responses"
    )

    class Config:
        env_prefix = "ANTHROPIC_"


class CohereConfig(BaseSettings):
    """Cohere API configuration."""
    
    api_key: Optional[str] = Field(
        default=None,
        description="Cohere API key"
    )
    model: str = Field(
        default="command-r-plus",
        description="Default Cohere model"
    )
    base_url: str = Field(
        default="https://api.cohere.ai",
        description="Cohere API base URL"
    )
    enabled: bool = Field(
        default=False,
        description="Enable Cohere provider"
    )
    max_tokens: int = Field(
        default=1000,
        description="Default max tokens for responses"
    )
    temperature: float = Field(
        default=0.7,
        description="Default temperature for responses"
    )

    class Config:
        env_prefix = "COHERE_"


class HuggingFaceConfig(BaseSettings):
    """Hugging Face Transformers configuration."""
    
    cache_dir: str = Field(
        default="./models",
        description="Directory to cache models"
    )
    device: str = Field(
        default="auto",
        description="Device to run models on (cpu, cuda, auto)"
    )
    enabled: bool = Field(
        default=True,
        description="Enable local Hugging Face models"
    )
    default_model: str = Field(
        default="microsoft/DialoGPT-medium",
        description="Default local model for fallback"
    )

    class Config:
        env_prefix = "HF_"


class KitchenConfig(BaseSettings):
    """Kitchen simulation configuration."""
    
    max_agents: int = Field(
        default=10,
        description="Maximum number of agents in simulation"
    )
    simulation_speed: float = Field(
        default=1.0,
        description="Simulation speed multiplier"
    )
    default_stress_level: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Default stress level for agents"
    )
    enable_crisis_events: bool = Field(
        default=True,
        description="Enable random crisis events"
    )
    max_concurrent_tasks: int = Field(
        default=5,
        description="Maximum concurrent tasks per agent"
    )

    class Config:
        env_prefix = "KITCHEN_"


class MetricsConfig(BaseSettings):
    """Metrics collection configuration."""
    
    collection_interval: int = Field(
        default=30,
        description="Metrics collection interval in seconds"
    )
    enable_export: bool = Field(
        default=True,
        description="Enable metrics export"
    )
    export_path: str = Field(
        default="./data/metrics",
        description="Path to export metrics"
    )
    export_formats: list[str] = Field(
        default=["json", "csv"],
        description="Export formats (json, csv, parquet)"
    )

    class Config:
        env_prefix = "METRICS_"


class APIConfig(BaseSettings):
    """API server configuration."""
    
    host: str = Field(
        default="0.0.0.0",
        description="API server host"
    )
    port: int = Field(
        default=8080,
        description="API server port"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    reload: bool = Field(
        default=False,
        description="Enable auto-reload"
    )
    cors_origins: list[str] = Field(
        default=["*"],
        description="CORS allowed origins"
    )
    title: str = Field(
        default="MasterChef-Bench API",
        description="API title"
    )
    version: str = Field(
        default="2.0.0",
        description="API version"
    )

    class Config:
        env_prefix = "API_"


class Settings(BaseSettings):
    """Main application settings."""
    
    # Environment
    environment: str = Field(
        default="development",
        description="Application environment"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # Data paths
    data_dir: Path = Field(
        default=Path("./data"),
        description="Data directory"
    )
    recipes_file: Path = Field(
        default=Path("./data/sample_recipes.csv"),
        description="Path to recipes CSV file"
    )
    
    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    anthropic: AnthropicConfig = Field(default_factory=AnthropicConfig)
    cohere: CohereConfig = Field(default_factory=CohereConfig)
    huggingface: HuggingFaceConfig = Field(default_factory=HuggingFaceConfig)
    kitchen: KitchenConfig = Field(default_factory=KitchenConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    api: APIConfig = Field(default_factory=APIConfig)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        (self.data_dir / "metrics").mkdir(exist_ok=True)

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ("development", "dev")

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() in ("production", "prod")

    def get_enabled_llm_providers(self) -> list[str]:
        """Get list of enabled LLM providers."""
        providers = []
        if self.openai.enabled and self.openai.api_key:
            providers.append("openai")
        if self.anthropic.enabled and self.anthropic.api_key:
            providers.append("anthropic")
        if self.cohere.enabled and self.cohere.api_key:
            providers.append("cohere")
        if self.huggingface.enabled:
            providers.append("huggingface")
        return providers


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def load_settings(config_file: Optional[Path] = None) -> Settings:
    """Load settings from file or environment."""
    global _settings
    
    if config_file and config_file.exists():
        # Load from YAML/TOML file if provided
        import yaml
        with open(config_file) as f:
            config_data = yaml.safe_load(f)
        _settings = Settings(**config_data)
    else:
        _settings = Settings()
    
    return _settings


# Backwards compatibility alias
Config = Settings