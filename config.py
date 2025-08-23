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
        default="gpt-4",
        description="Default OpenAI model"
    )
    enabled: bool = Field(
        default=False,
        description="Enable OpenAI provider"
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
    enabled: bool = Field(
        default=False,
        description="Enable Anthropic provider"
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
    enabled: bool = Field(
        default=False,
        description="Enable Cohere provider"
    )

    class Config:
        env_prefix = "COHERE_"


class HuggingFaceConfig(BaseSettings):
    """Hugging Face configuration."""
    
    api_key: Optional[str] = Field(
        default=None,
        description="Hugging Face API token"
    )
    model: str = Field(
        default="microsoft/DialoGPT-medium",
        description="Default model"
    )
    enabled: bool = Field(
        default=False,
        description="Enable Hugging Face provider"
    )

    class Config:
        env_prefix = "HF_"


class GitHubConfig(BaseSettings):
    """GitHub Models API configuration (FREE)."""
    
    api_key: Optional[str] = Field(
        default=None,
        description="GitHub token"
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="Default GitHub model"
    )
    enabled: bool = Field(
        default=False,
        description="Enable GitHub Models provider"
    )

    class Config:
        env_prefix = "GITHUB_"


class OllamaConfig(BaseSettings):
    """Ollama local LLM configuration (FREE)."""
    
    model: str = Field(
        default="llama3.2:1b",
        description="Default Ollama model"
    )
    enabled: bool = Field(
        default=True,
        description="Enable Ollama provider"
    )

    class Config:
        env_prefix = "OLLAMA_"


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
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
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
        if self.github.enabled and self.github.api_key:
            providers.append("github")
        if self.ollama.enabled:
            providers.append("ollama")
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
        
        # Transform YAML structure to match Settings structure
        transformed_data = {}
        
        # Handle top-level fields that should go into database config
        if 'database_url' in config_data:
            transformed_data['database'] = {'url': config_data['database_url']}
        
        # Copy other top-level fields that Settings expects
        for key in ['environment', 'log_level', 'debug', 'data_dir', 'recipes_file']:
            if key in config_data:
                transformed_data[key] = config_data[key]
        
        # Copy nested configurations directly
        for key in ['openai', 'anthropic', 'cohere', 'huggingface', 'github', 'ollama', 'kitchen', 'metrics']:
            if key in config_data:
                transformed_data[key] = config_data[key]
        
        _settings = Settings(**transformed_data)
    else:
        _settings = Settings()
    
    return _settings


# Backwards compatibility alias
Config = Settings