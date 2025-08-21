"""
Escoffier Kitchen Simulation Platform

A comprehensive multi-agent kitchen simulation system for research in:
- Multi-agent coordination and collaboration
- Large Language Model (LLM) integration
- Computational cooking and recipe optimization
- Crisis management and decision making
- Performance analysis and metrics collection

Components:
- Agent management with real LLM providers
- Kitchen simulation engine with realistic constraints
- Recipe management with pandas-based analytics
- Scenario execution with parallel processing
- Comprehensive metrics and visualization
- REST API server with FastAPI
- Command-line interface with Fire
"""

__version__ = "1.0.0"
__author__ = "Escoffier Research Team"
__description__ = "Multi-agent kitchen simulation and research platform"

from config import Config
from database import DatabaseManager
from agents import AgentManager, AgentContext, CoordinationMode
from kitchen import KitchenEngine
from recipes import RecipeManager, RecipeStep, RecipeIngredient, NutritionInfo
from scenarios import ScenarioExecutor, ScenarioConfig, ExecutionResult
from metrics import MetricsCollector, MetricType, AnalysisReport
from providers import LLMProvider, get_llm_provider
from api import EscoffierAPI, create_app
from cli import EscoffierCLI, main
import types

__all__ = [
    # Core configuration
    'Config',
    
    # Database
    'DatabaseManager',
    
    # Agent management
    'AgentManager',
    'AgentContext', 
    'CoordinationMode',
    
    # Kitchen simulation
    'KitchenEngine',
    
    # Recipe management
    'RecipeManager',
    'RecipeStep',
    'RecipeIngredient',
    'NutritionInfo',
    
    # Scenario execution
    'ScenarioExecutor',
    'ScenarioConfig',
    'ExecutionResult',
    
    # Metrics and analytics
    'MetricsCollector',
    'MetricType',
    'AnalysisReport',
    
    # LLM providers
    'LLMProvider',
    'get_llm_provider',
    
    # API server
    'EscoffierAPI',
    'create_app',
    
    # CLI
    'EscoffierCLI',
    'main',
    
    # Types
    'types',
]