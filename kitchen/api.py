"""
ChefBench API Server
Production-ready REST API for benchmark evaluation
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import asyncio
import uuid
import logging
from datetime import datetime

# Import ChefBench modules
from models.models import AgentRole, TaskType, LLMAgent
from providers import MultiAgentCoordinator
from recipes.dataset_parser import RecipeDatasetParser
from metrics import MetricsCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Request/Response Models
class AgentCreationRequest( BaseModel):
    name: str
    role: str = Field(..., pattern="^(HEAD_CHEF|SOUS_CHEF|CHEF_DE_PARTIE|LINE_COOK|PREP_COOK|KITCHEN_PORTER)$")
    model_name: str = Field(default="cohere/command-r")
    device: str = Field(..., pattern="^(cpu|gpu)$")


class TeamCreationRequest(BaseModel):
    model_name: str
    team_size: int = Field(4, ge=2, le=6)
    roles: Optional[List[str]] = None


class MixedTeamRequest(BaseModel):
    agents: List[Dict[str, str]]  # [{"model": "model_name", "role": "ROLE_NAME"}]


class ScenarioExecutionRequest(BaseModel):
    scenario_type: str = Field("standard", pattern="^(standard|crisis|collaboration|complex)$")
    duration_seconds: int = Field(300, ge=60, le=3600)
    num_tasks: int = Field(10, ge=1, le=50)
    use_dataset: bool = True


class ChefBenchAPI:
    """Main API server for ChefBench evaluation"""
    
    def __init__(self):
        self.app = FastAPI(
            title="ChefBench API",
            description="Multi-agent LLM kitchen coordination benchmark",
            version="1.0.0"
        )
        
        # Initialize components
        self.coordinator = MultiAgentCoordinator()
        self.dataset_parser = RecipeDatasetParser()
        self.metrics_collector = MetricsCollector()
        
        # Active evaluations
        self.active_evaluations: Dict[str, Dict] = {}
        
        # Setup routes
        self.setup_routes()

    def setup_routes(self):
        """Configure all API routes"""

        @self.app.get("/")
        async def root():
            return {
                "name": "ChefBench API",
                "version": "1.0.0",
                "status": "operational",
                "components": {
                    "coordinator": "ready",
                    "dataset": "ready" if self.dataset_parser.loaded else "not_loaded"
                }
            }


        async def _load_dataset(file_path: str):
            """Load Kaggle recipe dataset"""
            success = self.dataset_parser.load_kaggle_dataset(file_path)
            if not success:
                raise HTTPException(400, f"Failed to load dataset from {file_path}")
            
            stats = self.dataset_parser.get_statistics()
            return {
                "status": "loaded",
                "statistics": stats
            }


        @self.app.get("/dataset/stats")
        async def get_dataset_stats():
            """Get dataset statistics"""
            if not self.dataset_parser.loaded:
                raise HTTPException(400, "Dataset not loaded")
            
            return self.dataset_parser.get_statistics()
        
        @self.app.post("/agents/create")
        async def create_agent(request: AgentCreationRequest):
            """Create a single agent"""
            try:
                role = AgentRole[request.role]
                agent = self.coordinator.create_agent(
                    request.name,
                    role,
                    request.model_name
                    
                )
                
                return {
                    "status": "created",
                    "agent": {
                        "name": agent.name,
                        "role": agent.role.name,
                        "model": agent.model_name,
                        "available_tasks": [t.function_name for t in agent.available_tasks]
                    }
                }
            except Exception as e:
                raise HTTPException(400, f"Failed to create agent: {str(e)}")
        
        @self.app.post("/teams/create_uniform")
        async def create_uniform_team(request: TeamCreationRequest):
            """Create team with same model"""
            try:
                roles = None
                if request.roles:
                    roles = [AgentRole[r] for r in request.roles]
                
                team = self.coordinator.create_agent_team(
                    request.model_name,
                    request.team_size,
                    roles
                )
                
                return {
                    "status": "created",
                    "team_size": len(team),
                    "agents": [
                        {
                            "name": agent.name,
                            "role": agent.role.name,
                            "model": agent.model_name
                        }
                        for agent in team
                    ]
                }
            except Exception as e:
                raise HTTPException(400, f"Failed to create team: {str(e)}")
        
        @self.app.post("/teams/create_mixed")
        async def create_mixed_team(request: MixedTeamRequest):
            """Create team with different models"""
            try:
                provider_models = [
                    (agent["model"], AgentRole[agent["role"]])
                    for agent in request.agents
                ]
                
                team = self.coordinator.create_mixed_provider_team(provider_models)
                
                return {
                    "status": "created",
                    "team_size": len(team),
                    "agents": [
                        {
                            "name": agent.name,
                            "role": agent.role.name,
                            "model": agent.model_name
                        }
                        for agent in team
                    ]
                }
            except Exception as e:
                raise HTTPException(400, f"Failed to create mixed team: {str(e)}")
        
        @self.app.get("/agents/list")
        async def list_agents():
            """List all registered agents"""
            agents = []
            for name, agent in self.coordinator.agents.items():
                metrics = agent.get_metrics()
                agents.append({
                    "name": name,
                    "role": agent.role.name,
                    "model": agent.model_name,
                    "metrics": metrics
                })
            
            return {
                "total_agents": len(agents),
                "agents": agents
            }
        
        @self.app.post("/scenarios/execute")
        async def execute_scenario(
            request: ScenarioExecutionRequest,
            background_tasks: BackgroundTasks
        ):
            """Execute a benchmark scenario"""
            if len(self.coordinator.agents) < 2:
                raise HTTPException(400, "Need at least 2 agents to run scenario")
            
            evaluation_id = str(uuid.uuid4())
            
            # Generate tasks based on scenario type
            tasks = self._generate_scenario_tasks(
                request.scenario_type,
                request.num_tasks,
                request.use_dataset
            )
            
            # Initialize evaluation
            self.active_evaluations[evaluation_id] = {
                "id": evaluation_id,
                "status": "running",
                "started_at": datetime.now().isoformat(),
                "config": request.dict(),
                "result": None
            }
            
            # Start execution in background
            background_tasks.add_task(
                self._run_scenario,
                evaluation_id,
                tasks,
                request.duration_seconds,
                request.scenario_type
            )
            
            return {
                "evaluation_id": evaluation_id,
                "status": "started",
                "message": f"Scenario started with {len(tasks)} tasks"
            }
        
        @self.app.get("/scenarios/{evaluation_id}/status")
        async def get_scenario_status(evaluation_id: str):
            """Get scenario execution status"""
            if evaluation_id not in self.active_evaluations:
                raise HTTPException(404, "Evaluation not found")
            
            eval_data = self.active_evaluations[evaluation_id]
            return {
                "evaluation_id": evaluation_id,
                "status": eval_data["status"],
                "started_at": eval_data["started_at"],
                "config": eval_data["config"]
            }
        
        @self.app.get("/scenarios/{evaluation_id}/results")
        async def get_scenario_results(evaluation_id: str):
            """Get scenario results"""
            if evaluation_id not in self.active_evaluations:
                raise HTTPException(404, "Evaluation not found")
            
            eval_data = self.active_evaluations[evaluation_id]
            if eval_data["status"] != "completed":
                raise HTTPException(400, f"Evaluation is {eval_data['status']}")
            
            return eval_data["result"]
        
        @self.app.get("/metrics/charts")
        async def generate_charts():
            """Generate visualization charts"""
            chart_files = self.metrics_collector.generate_charts()
            
            if not chart_files:
                raise HTTPException(400, "No data available for charts")
            
            return {
                "status": "generated",
                "files": [str(f) for f in chart_files]
            }
        
        @self.app.get("/metrics/report")
        async def generate_report():
            """Generate comprehensive report"""
            report_file = self.metrics_collector.generate_report()
            
            return FileResponse(
                path=report_file,
                media_type="text/markdown",
                filename=report_file.name
            )
        
        @self.app.get("/metrics/export")
        async def export_metrics():
            """Export metrics to CSV"""
            csv_files = self.metrics_collector.export_to_csv()
            
            return {
                "status": "exported",
                "files": [str(f) for f in csv_files]
            }
        
        @self.app.post("/metrics/compare_models")
        async def compare_models(model_groups: Dict[str, List[str]]):
            """Compare performance across models"""
            comparison = self.metrics_collector.analyze_model_comparison(model_groups)
            
            return {
                "status": "analyzed",
                "comparison": comparison
            }
        
        @self.app.delete("/reset")
        async def reset_system():
            """Reset the entire system"""
            self.coordinator.reset()
            self.coordinator.agents.clear()
            self.active_evaluations.clear()
            
            return {"status": "reset", "message": "System reset successfully"}
    
    def _generate_scenario_tasks(
        self,
        scenario_type: str,
        num_tasks: int,
        use_dataset: bool
    ) -> List[Tuple[TaskType, Dict]]:
        """Generate tasks for a scenario"""
        tasks = []
        
        # Get inventory from dataset if available
        if use_dataset and self.dataset_parser.loaded:
            inventory = self.dataset_parser.generate_kitchen_inventory("medium")
            ingredients = list(inventory.keys())
        else:
            ingredients = ["salt", "pepper", "oil", "flour", "eggs", "milk", "butter"]
        
        # Define task distributions by scenario type
        if scenario_type == "standard":
            task_distribution = [
                (TaskType.MENU_PLANNING, 1),
                (TaskType.INGREDIENT_PREPARATION, 3),
                (TaskType.COOKING_EXECUTION, 3),
                (TaskType.PLATING_DESIGN, 2),
                (TaskType.QUALITY_CONTROL, 1)
            ]
        elif scenario_type == "crisis":
            task_distribution = [
                (TaskType.EQUIPMENT_MAINTENANCE, 2),
                (TaskType.INVENTORY_MANAGEMENT, 2),
                (TaskType.COOKING_EXECUTION, 3),
                (TaskType.TIMING_COORDINATION, 3)
            ]
        elif scenario_type == "collaboration":
            task_distribution = [
                (TaskType.STAFF_COORDINATION, 2),
                (TaskType.COMMUNICATION, 3),
                (TaskType.SAUCE_PREPARATION, 2),
                (TaskType.PLATING_DESIGN, 3)
            ]
        else:  # complex
            task_distribution = [
                (TaskType.MENU_PLANNING, 1),
                (TaskType.RECIPE_MODIFICATION, 2),
                (TaskType.STATION_MANAGEMENT, 2),
                (TaskType.COOKING_EXECUTION, 2),
                (TaskType.TEMPERATURE_MONITORING, 1),
                (TaskType.QUALITY_CONTROL, 2)
            ]
        
        # Generate tasks based on distribution
        task_count = 0
        while task_count < num_tasks:
            for task_type, weight in task_distribution:
                for _ in range(weight):
                    if task_count >= num_tasks:
                        break
                    
                    context = {
                        "ingredients": ingredients[:10],
                        "time_limit": 300,
                        "difficulty": scenario_type,
                        "task_number": task_count + 1
                    }
                    
                    tasks.append((task_type, context))
                    task_count += 1
        
        return tasks[:num_tasks]
    
    async def _run_scenario(
        self,
        evaluation_id: str,
        tasks: List[Tuple[TaskType, Dict]],
        duration_seconds: int,
        scenario_type: str
    ):
        """Run scenario execution"""
        try:
            # Reset coordinator for fresh execution
            self.coordinator.reset()
            
            # Execute scenario
            result = await self.coordinator.execute_scenario(tasks, duration_seconds)
            
            # Record metrics
            self.metrics_collector.record_scenario(
                scenario_type,
                result,
                self.active_evaluations[evaluation_id]["config"]
            )
            
            # Update evaluation
            self.active_evaluations[evaluation_id]["status"] = "completed"
            self.active_evaluations[evaluation_id]["result"] = result
            
            logger.info(f"Scenario {evaluation_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Scenario {evaluation_id} failed: {str(e)}")
            self.active_evaluations[evaluation_id]["status"] = "failed"
            self.active_evaluations[evaluation_id]["error"] = str(e)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    api = ChefBenchAPI()
    return api.app


if __name__ == "__main__":
    import uvicorn
    
    # Create app
    app = create_app()
    
    # Run server
    uvicorn.run(
        app,
        host="localhost",
        port=8000,
        log_level="info"
    )
