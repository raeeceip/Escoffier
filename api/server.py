"""
FastAPI Server - REST API for Escoffier kitchen simulation
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import logging
import asyncio
from datetime import datetime
import uuid
from pathlib import Path

from config import Config
from database import DatabaseManager
from agents.manager import AgentManager
from kitchen.engine import KitchenEngine
from recipes.manager import RecipeManager
from scenarios.executor import ScenarioExecutor, ScenarioConfig
from metrics.collector import MetricsCollector
from escoffier_types import AgentType, ScenarioType, TaskType

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Pydantic models for API
class AgentCreateRequest(BaseModel):
    name: str = Field(..., description="Agent name")
    agent_type: AgentType = Field(..., description="Type of agent")
    skills: List[str] = Field(default=[], description="Agent skills")
    llm_provider: str = Field(default="openai", description="LLM provider to use")

class AgentResponse(BaseModel):
    id: str
    name: str
    agent_type: str
    status: str
    skills: List[str]
    performance_score: float
    stress_level: float
    energy_level: float

class TaskAssignRequest(BaseModel):
    agent_id: str = Field(..., description="Target agent ID")
    task_type: TaskType = Field(..., description="Type of task")
    description: str = Field(..., description="Task description")
    priority: int = Field(default=1, description="Task priority (1-5)")
    parameters: Dict[str, Any] = Field(default={}, description="Task parameters")

class TaskResponse(BaseModel):
    id: str
    agent_id: str
    task_type: str
    description: str
    status: str
    priority: int
    assigned_at: datetime
    
class ScenarioCreateRequest(BaseModel):
    name: str = Field(..., description="Scenario name")
    scenario_type: ScenarioType = Field(..., description="Type of scenario")
    duration_minutes: int = Field(default=60, description="Scenario duration")
    max_agents: int = Field(default=4, description="Maximum number of agents")
    recipes: List[str] = Field(default=[], description="Recipe IDs to use")
    difficulty_level: str = Field(default="medium", description="Difficulty level")
    time_pressure: float = Field(default=1.0, description="Time pressure multiplier")
    crisis_probability: float = Field(default=0.1, description="Crisis event probability")

class ScenarioResponse(BaseModel):
    scenario_id: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: float
    tasks_completed: int
    tasks_failed: int
    recipes_completed: int
    quality_score: float
    efficiency_score: float
    collaboration_score: float

class RecipeSearchRequest(BaseModel):
    query: Optional[str] = None
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None
    max_time: Optional[int] = None
    ingredients: List[str] = Field(default=[])
    techniques: List[str] = Field(default=[])

class RecipeResponse(BaseModel):
    id: str
    name: str
    cuisine: str
    difficulty: str
    prep_time: float
    cook_time: float
    total_time: float
    servings: int
    techniques: List[str]
    equipment: List[str]

class KitchenStateResponse(BaseModel):
    stations: Dict[str, Dict]
    equipment: Dict[str, Dict]
    ingredients: Dict[str, Dict]
    temperature: float
    humidity: float
    active_agents: List[str]
    ongoing_tasks: List[str]

class MetricsResponse(BaseModel):
    timestamp: datetime
    total_scenarios: int
    successful_scenarios: int
    failed_scenarios: int
    average_duration: float
    average_quality: float
    average_efficiency: float
    agent_count: int
    active_scenarios: int


class EscoffierAPI:
    """FastAPI application for Escoffier kitchen simulation"""
    
    def __init__(self, config: Config):
        self.config = config
        self.app = FastAPI(
            title="Escoffier Kitchen Simulation API",
            description="Multi-agent kitchen simulation and research platform",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Initialize components
        self.db_manager: Optional[DatabaseManager] = None
        self.agent_manager: Optional[AgentManager] = None
        self.kitchen_engine: Optional[KitchenEngine] = None
        self.recipe_manager: Optional[RecipeManager] = None
        self.scenario_executor: Optional[ScenarioExecutor] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        
        # Add routes
        self._add_routes()
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing Escoffier API components")
        
        # Initialize database
        self.db_manager = DatabaseManager(self.config)
        await self.db_manager.initialize()
        
        # Initialize components
        self.kitchen_engine = KitchenEngine(self.config)
        await self.kitchen_engine.initialize()
        
        self.agent_manager = AgentManager(self.config, self.db_manager, self.kitchen_engine)
        await self.agent_manager.initialize()
        
        self.recipe_manager = RecipeManager(self.config, self.db_manager)
        await self.recipe_manager.initialize()
        
        self.scenario_executor = ScenarioExecutor(
            self.config, self.db_manager, self.agent_manager, 
            self.kitchen_engine, self.recipe_manager
        )
        await self.scenario_executor.initialize()
        
        self.metrics_collector = MetricsCollector(self.config, self.db_manager)
        await self.metrics_collector.initialize()
        
        logger.info("Escoffier API initialization complete")
        
    def _add_routes(self):
        """Add all API routes"""
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.utcnow()}
            
        # Agent management routes
        @self.app.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
        async def create_agent(request: AgentCreateRequest):
            """Create a new agent"""
            if not self.agent_manager:
                raise HTTPException(status_code=500, detail="Agent manager not initialized")
                
            try:
                agent_id = await self.agent_manager.create_agent(
                    name=request.name,
                    agent_type=request.agent_type,
                    skills=request.skills,
                    llm_provider=request.llm_provider
                )
                
                agent_context = self.agent_manager.agents[agent_id]
                return AgentResponse(
                    id=agent_id,
                    name=agent_context.name,
                    agent_type=agent_context.agent_type.value,
                    status=agent_context.status.value,
                    skills=agent_context.skills,
                    performance_score=agent_context.performance_score,
                    stress_level=agent_context.stress_level,
                    energy_level=agent_context.energy_level
                )
            except Exception as e:
                logger.error(f"Failed to create agent: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/agents", response_model=List[AgentResponse])
        async def list_agents():
            """List all agents"""
            if not self.agent_manager:
                raise HTTPException(status_code=500, detail="Agent manager not initialized")
                
            agents = []
            for agent_id, agent_context in self.agent_manager.agents.items():
                agents.append(AgentResponse(
                    id=agent_id,
                    name=agent_context.name,
                    agent_type=agent_context.agent_type.value,
                    status=agent_context.status.value,
                    skills=agent_context.skills,
                    performance_score=agent_context.performance_score,
                    stress_level=agent_context.stress_level,
                    energy_level=agent_context.energy_level
                ))
            return agents
            
        @self.app.get("/agents/{agent_id}", response_model=AgentResponse)
        async def get_agent(agent_id: str):
            """Get specific agent details"""
            if not self.agent_manager:
                raise HTTPException(status_code=500, detail="Agent manager not initialized")
                
            if agent_id not in self.agent_manager.agents:
                raise HTTPException(status_code=404, detail="Agent not found")
                
            agent_context = self.agent_manager.agents[agent_id]
            return AgentResponse(
                id=agent_id,
                name=agent_context.name,
                agent_type=agent_context.agent_type.value,
                status=agent_context.status.value,
                skills=agent_context.skills,
                performance_score=agent_context.performance_score,
                stress_level=agent_context.stress_level,
                energy_level=agent_context.energy_level
            )
            
        @self.app.get("/agents/status")
        async def get_team_status():
            """Get overall team status"""
            if not self.agent_manager:
                raise HTTPException(status_code=500, detail="Agent manager not initialized")
                
            return self.agent_manager.get_team_status()
            
        # Task management routes
        @self.app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
        async def assign_task(request: TaskAssignRequest):
            """Assign a task to an agent"""
            if not self.agent_manager:
                raise HTTPException(status_code=500, detail="Agent manager not initialized")
                
            try:
                task_data = {
                    'type': request.task_type.value,
                    'description': request.description,
                    'priority': request.priority,
                    'parameters': request.parameters
                }
                
                task_id = await self.agent_manager.assign_task(request.agent_id, task_data)
                
                # Get task details from database
                with self.db_manager.get_session() as session:
                    from database.models import Task
                    task = session.query(Task).filter(Task.id == task_id).first()
                    if task:
                        return TaskResponse(
                            id=task.id,
                            agent_id=task.agent_id,
                            task_type=task.task_type,
                            description=task.description,
                            status=task.status,
                            priority=task.priority,
                            assigned_at=task.assigned_at
                        )
                    else:
                        raise HTTPException(status_code=500, detail="Task created but not found")
                        
            except Exception as e:
                logger.error(f"Failed to assign task: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/tasks")
        async def list_tasks(agent_id: Optional[str] = None, status: Optional[str] = None):
            """List tasks with optional filters"""
            if not self.db_manager:
                raise HTTPException(status_code=500, detail="Database not initialized")
                
            with self.db_manager.get_session() as session:
                from database.models import Task
                query = session.query(Task)
                
                if agent_id:
                    query = query.filter(Task.agent_id == agent_id)
                if status:
                    query = query.filter(Task.status == status)
                    
                tasks = query.all()
                
                return [
                    TaskResponse(
                        id=task.id,
                        agent_id=task.agent_id,
                        task_type=task.task_type,
                        description=task.description,
                        status=task.status,
                        priority=task.priority,
                        assigned_at=task.assigned_at
                    )
                    for task in tasks
                ]
                
        # Kitchen state routes
        @self.app.get("/kitchen/state", response_model=KitchenStateResponse)
        async def get_kitchen_state():
            """Get current kitchen state"""
            if not self.kitchen_engine:
                raise HTTPException(status_code=500, detail="Kitchen engine not initialized")
                
            state = await self.kitchen_engine.get_kitchen_state()
            return KitchenStateResponse(**state)
            
        @self.app.post("/kitchen/reset")
        async def reset_kitchen():
            """Reset kitchen to initial state"""
            if not self.kitchen_engine:
                raise HTTPException(status_code=500, detail="Kitchen engine not initialized")
                
            await self.kitchen_engine.reset_kitchen()
            return {"status": "kitchen reset successfully"}
            
        # Recipe management routes
        @self.app.post("/recipes/search", response_model=List[RecipeResponse])
        async def search_recipes(request: RecipeSearchRequest):
            """Search recipes with filters"""
            if not self.recipe_manager:
                raise HTTPException(status_code=500, detail="Recipe manager not initialized")
                
            try:
                results_df = self.recipe_manager.search_recipes(
                    query=request.query,
                    cuisine=request.cuisine,
                    difficulty=request.difficulty,
                    max_time=request.max_time,
                    ingredients=request.ingredients,
                    techniques=request.techniques
                )
                
                recipes = []
                for _, row in results_df.iterrows():
                    recipe_id = row['id'] if 'id' in row else row.name
                    cached_recipe = self.recipe_manager.recipe_cache.get(str(recipe_id))
                    
                    if cached_recipe:
                        recipes.append(RecipeResponse(
                            id=str(recipe_id),
                            name=cached_recipe['name'],
                            cuisine=cached_recipe['cuisine'],
                            difficulty=cached_recipe['difficulty'],
                            prep_time=cached_recipe['prep_time'],
                            cook_time=cached_recipe['cook_time'],
                            total_time=cached_recipe['total_time'],
                            servings=cached_recipe['servings'],
                            techniques=cached_recipe['techniques'],
                            equipment=cached_recipe['equipment']
                        ))
                        
                return recipes
                
            except Exception as e:
                logger.error(f"Failed to search recipes: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/recipes/recommendations")
        async def get_recipe_recommendations(
            agent_skills: str = "",
            available_ingredients: str = "",
            time_limit: int = 60,
            difficulty: str = "medium"
        ):
            """Get recipe recommendations based on constraints"""
            if not self.recipe_manager:
                raise HTTPException(status_code=500, detail="Recipe manager not initialized")
                
            try:
                skills_list = [s.strip() for s in agent_skills.split(",")] if agent_skills else []
                ingredients_list = [i.strip() for i in available_ingredients.split(",")] if available_ingredients else []
                
                recommendations = self.recipe_manager.get_recipe_recommendations(
                    agent_skills=skills_list,
                    available_ingredients=ingredients_list,
                    time_limit=time_limit,
                    difficulty_preference=difficulty
                )
                
                return recommendations
                
            except Exception as e:
                logger.error(f"Failed to get recommendations: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/recipes/statistics")
        async def get_recipe_statistics():
            """Get recipe database statistics"""
            if not self.recipe_manager:
                raise HTTPException(status_code=500, detail="Recipe manager not initialized")
                
            return self.recipe_manager.get_recipe_statistics()
            
        # Scenario execution routes
        @self.app.post("/scenarios/execute", response_model=ScenarioResponse)
        async def execute_scenario(request: ScenarioCreateRequest, background_tasks: BackgroundTasks):
            """Execute a scenario"""
            if not self.scenario_executor:
                raise HTTPException(status_code=500, detail="Scenario executor not initialized")
                
            try:
                scenario_id = str(uuid.uuid4())
                scenario_config = ScenarioConfig(
                    scenario_id=scenario_id,
                    scenario_type=request.scenario_type,
                    duration_minutes=request.duration_minutes,
                    max_agents=request.max_agents,
                    recipes=request.recipes,
                    difficulty_level=request.difficulty_level,
                    time_pressure=request.time_pressure,
                    crisis_probability=request.crisis_probability
                )
                
                # Execute scenario in background
                result = await self.scenario_executor.execute_scenario(scenario_config)
                
                return ScenarioResponse(
                    scenario_id=result.scenario_id,
                    status=result.status.value if hasattr(result.status, 'value') else result.status,
                    start_time=result.start_time,
                    end_time=result.end_time,
                    duration_seconds=result.duration_seconds,
                    tasks_completed=result.tasks_completed,
                    tasks_failed=result.tasks_failed,
                    recipes_completed=result.recipes_completed,
                    quality_score=result.quality_score,
                    efficiency_score=result.efficiency_score,
                    collaboration_score=result.collaboration_score
                )
                
            except Exception as e:
                logger.error(f"Failed to execute scenario: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/scenarios/{scenario_id}", response_model=ScenarioResponse)
        async def get_scenario_result(scenario_id: str):
            """Get scenario execution result"""
            if not self.scenario_executor:
                raise HTTPException(status_code=500, detail="Scenario executor not initialized")
                
            if scenario_id not in self.scenario_executor.execution_results:
                raise HTTPException(status_code=404, detail="Scenario not found")
                
            result = self.scenario_executor.execution_results[scenario_id]
            return ScenarioResponse(
                scenario_id=result.scenario_id,
                status=result.status.value if hasattr(result.status, 'value') else result.status,
                start_time=result.start_time,
                end_time=result.end_time,
                duration_seconds=result.duration_seconds,
                tasks_completed=result.tasks_completed,
                tasks_failed=result.tasks_failed,
                recipes_completed=result.recipes_completed,
                quality_score=result.quality_score,
                efficiency_score=result.efficiency_score,
                collaboration_score=result.collaboration_score
            )
            
        @self.app.get("/scenarios")
        async def list_scenarios():
            """List all scenario results"""
            if not self.scenario_executor:
                raise HTTPException(status_code=500, detail="Scenario executor not initialized")
                
            scenarios = []
            for result in self.scenario_executor.execution_results.values():
                scenarios.append(ScenarioResponse(
                    scenario_id=result.scenario_id,
                    status=result.status.value if hasattr(result.status, 'value') else result.status,
                    start_time=result.start_time,
                    end_time=result.end_time,
                    duration_seconds=result.duration_seconds,
                    tasks_completed=result.tasks_completed,
                    tasks_failed=result.tasks_failed,
                    recipes_completed=result.recipes_completed,
                    quality_score=result.quality_score,
                    efficiency_score=result.efficiency_score,
                    collaboration_score=result.collaboration_score
                ))
            return scenarios
            
        # Metrics and analytics routes
        @self.app.get("/metrics", response_model=MetricsResponse)
        async def get_metrics():
            """Get current system metrics"""
            if not self.metrics_collector:
                raise HTTPException(status_code=500, detail="Metrics collector not initialized")
                
            try:
                await self.metrics_collector.refresh_data()
                
                # Get execution summary
                summary = self.scenario_executor.get_execution_summary() if self.scenario_executor else {}
                metrics = summary.get('metrics', {})
                
                return MetricsResponse(
                    timestamp=datetime.utcnow(),
                    total_scenarios=metrics.get('total_scenarios', 0),
                    successful_scenarios=metrics.get('successful_scenarios', 0),
                    failed_scenarios=metrics.get('failed_scenarios', 0),
                    average_duration=metrics.get('average_duration', 0.0),
                    average_quality=metrics.get('average_quality', 0.0),
                    average_efficiency=metrics.get('average_efficiency', 0.0),
                    agent_count=len(self.agent_manager.agents) if self.agent_manager else 0,
                    active_scenarios=summary.get('active_scenarios', 0)
                )
                
            except Exception as e:
                logger.error(f"Failed to get metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/metrics/analysis")
        async def get_analysis():
            """Get comprehensive analysis"""
            if not self.metrics_collector:
                raise HTTPException(status_code=500, detail="Metrics collector not initialized")
                
            try:
                report = self.metrics_collector.generate_comprehensive_report()
                return report.to_dict()
            except Exception as e:
                logger.error(f"Failed to generate analysis: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/metrics/dashboard")
        async def get_dashboard_data():
            """Get real-time dashboard data"""
            if not self.metrics_collector:
                raise HTTPException(status_code=500, detail="Metrics collector not initialized")
                
            try:
                return self.metrics_collector.get_real_time_dashboard_data()
            except Exception as e:
                logger.error(f"Failed to get dashboard data: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/metrics/export")
        async def export_metrics(format: str = "csv"):
            """Export metrics data"""
            if not self.metrics_collector:
                raise HTTPException(status_code=500, detail="Metrics collector not initialized")
                
            try:
                file_path = self.metrics_collector.export_metrics_data(format)
                return FileResponse(
                    path=file_path,
                    filename=f"metrics_export.{format}",
                    media_type="application/octet-stream"
                )
            except Exception as e:
                logger.error(f"Failed to export metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # Communication routes
        @self.app.post("/communication")
        async def send_communication(
            from_agent_id: str,
            to_agent_id: str,
            message: str
        ):
            """Send communication between agents"""
            if not self.agent_manager:
                raise HTTPException(status_code=500, detail="Agent manager not initialized")
                
            try:
                success = await self.agent_manager.facilitate_communication(
                    from_agent_id, to_agent_id, message
                )
                
                if success:
                    return {"status": "message sent successfully"}
                else:
                    raise HTTPException(status_code=400, detail="Failed to send message")
                    
            except Exception as e:
                logger.error(f"Failed to send communication: {e}")
                raise HTTPException(status_code=500, detail=str(e))


# Create global app instance
def create_app(config: Config) -> FastAPI:
    """Create and configure FastAPI application"""
    api = EscoffierAPI(config)
    return api.app


# Startup event
async def startup_app(api: EscoffierAPI):
    """Startup event handler"""
    await api.initialize()


# Shutdown event
async def shutdown_app(api: EscoffierAPI):
    """Shutdown event handler"""
    if api.agent_manager:
        await api.agent_manager.cleanup()
    if api.scenario_executor:
        await api.scenario_executor.cleanup()
    if api.db_manager:
        await api.db_manager.close()
        
    logger.info("Escoffier API shutdown complete")