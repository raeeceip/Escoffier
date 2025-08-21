"""
Scenario Execution Engine - Orchestrates multi-agent kitchen scenarios
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum
import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

from config import Config
from database.models import Scenario, Agent, Recipe, Task, AgentAction, Communication, MetricsSnapshot
from database import DatabaseManager
from agents.manager import AgentManager
from kitchen.engine import KitchenEngine
from recipes.manager import RecipeManager
from recipes.task_generator import RecipeTaskGenerator
from escoffier_types import ScenarioType, ScenarioStatus, AgentType, TaskType, AgentStatus, TaskStatus

logger = logging.getLogger(__name__)


class ExecutionPhase(Enum):
    """Scenario execution phases"""
    SETUP = "setup"
    PREPARATION = "preparation"
    COOKING = "cooking"
    PLATING = "plating"
    SERVICE = "service"
    CLEANUP = "cleanup"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ScenarioConfig:
    """Configuration for a scenario execution"""
    scenario_id: str
    scenario_type: ScenarioType
    duration_minutes: int
    max_agents: int
    recipes: List[str]
    difficulty_level: str
    time_pressure: float = 1.0  # Multiplier for time constraints
    crisis_probability: float = 0.1  # Probability of crisis events
    collaboration_required: bool = True
    quality_threshold: float = 0.8
    efficiency_threshold: float = 0.7
    
    # Performance parameters
    parallel_tasks: bool = True
    max_concurrent_agents: int = 4
    communication_frequency: int = 30  # seconds between status updates
    
    # Research parameters
    collect_detailed_metrics: bool = True
    record_communications: bool = True
    save_intermediate_states: bool = True


@dataclass
class ExecutionResult:
    """Results from scenario execution"""
    scenario_id: str
    status: ScenarioStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Scenario metadata
    scenario_type: str = "collaboration_test"  # Default type
    
    # Performance metrics
    tasks_completed: int = 0
    tasks_failed: int = 0
    recipes_completed: int = 0
    quality_score: float = 0.0
    efficiency_score: float = 0.0
    collaboration_score: float = 0.0
    
    # Communication tracking
    messages_sent: int = 0
    total_response_time: float = 0.0  # Sum of all response times
    response_count: int = 0  # Number of responses tracked
    
    # Agent performance
    agent_performances: Dict[str, Dict] = field(default_factory=dict)
    communications: List[Dict] = field(default_factory=list)
    crisis_events: List[Dict] = field(default_factory=list)
    
    # Detailed logs
    phase_timings: Dict[str, float] = field(default_factory=dict)
    kitchen_states: List[Dict] = field(default_factory=list)
    error_log: List[Dict] = field(default_factory=list)
    
    def get_avg_response_time(self) -> float:
        """Calculate average response time"""
        if self.response_count == 0:
            return 0.0
        return self.total_response_time / self.response_count
    
    def record_response_time(self, response_time: float):
        """Record a response time for tracking"""
        self.total_response_time += response_time
        self.response_count += 1
    
    def record_message(self):
        """Record a sent message"""
        self.messages_sent += 1
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary for storage"""
        return {
            'scenario_id': self.scenario_id,
            'status': self.status.value if isinstance(self.status, ScenarioStatus) else self.status,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'scenario_type': self.scenario_type,
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed,
            'recipes_completed': self.recipes_completed,
            'quality_score': self.quality_score,
            'efficiency_score': self.efficiency_score,
            'collaboration_score': self.collaboration_score,
            'messages_sent': self.messages_sent,
            'avg_response_time': self.get_avg_response_time(),
            'agent_performances': self.agent_performances,
            'communications': self.communications,
            'crisis_events': self.crisis_events,
            'phase_timings': self.phase_timings,
            'kitchen_states': self.kitchen_states,
            'error_log': self.error_log
        }


class ScenarioExecutor:
    """Executes multi-agent kitchen scenarios with parallel processing and communication tracking"""
    
    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        agent_manager: AgentManager,
        kitchen_engine: KitchenEngine,
        recipe_manager: RecipeManager
    ):
        self.config = config
        self.db_manager = db_manager
        self.agent_manager = agent_manager
        self.kitchen_engine = kitchen_engine
        self.recipe_manager = recipe_manager
        self.task_generator = RecipeTaskGenerator()
        
        # Execution state
        self.active_scenarios: Dict[str, Dict] = {}
        self.execution_results: Dict[str, ExecutionResult] = {}
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.current_result = None  # For event tracking and communication analysis
        
        # Event system
        self.event_handlers: Dict[str, List[Callable]] = {
            'scenario_started': [],
            'phase_changed': [],
            'task_completed': [],
            'crisis_occurred': [],
            'scenario_completed': []
        }
        
        # Performance tracking
        self.execution_metrics = {
            'total_scenarios': 0,
            'successful_scenarios': 0,
            'failed_scenarios': 0,
            'average_duration': 0.0,
            'average_quality': 0.0,
            'average_efficiency': 0.0
        }
        
    async def initialize(self):
        """Initialize scenario executor"""
        await self.load_scenario_templates()
        logger.info("Scenario executor initialized")
        
    async def load_scenario_templates(self):
        """Load scenario templates from database"""
        with self.db_manager.get_session() as session:
            scenarios = session.query(Scenario).all()
            
            for scenario in scenarios:
                logger.info(f"Loaded scenario template: {scenario.name} ({scenario.scenario_type})")
                
    async def execute_scenario(self, scenario_config: ScenarioConfig) -> ExecutionResult:
        """Execute a complete scenario with communication tracking"""
        logger.info(f"Starting scenario execution: {scenario_config.scenario_id}")
        
        result = ExecutionResult(
            scenario_id=scenario_config.scenario_id,
            status=ScenarioStatus.RUNNING,
            start_time=datetime.utcnow(),
            scenario_type=scenario_config.scenario_type.value if hasattr(scenario_config, 'scenario_type') and hasattr(scenario_config.scenario_type, 'value') else "collaboration_test"
        )
        
        # Initialize communication tracking
        result.metrics = {
            'communications': [],
            'communication_patterns': {},
            'events': []
        }
        
        # Store for event tracking
        self.current_result = result
        
        try:
            # Store active scenario
            self.active_scenarios[scenario_config.scenario_id] = {
                'config': scenario_config,
                'result': result,
                'current_phase': ExecutionPhase.SETUP,
                'start_time': time.time()
            }
            
            # Execute phases sequentially
            phases = [
                ExecutionPhase.SETUP,
                ExecutionPhase.PREPARATION,
                ExecutionPhase.COOKING,
                ExecutionPhase.PLATING,
                ExecutionPhase.SERVICE,
                ExecutionPhase.CLEANUP
            ]
            
            for phase in phases:
                phase_start = time.time()
                await self._execute_phase(scenario_config, result, phase)
                phase_duration = time.time() - phase_start
                result.phase_timings[phase.value] = phase_duration
                
                # Check for early termination
                if result.status in [ScenarioStatus.FAILED, ScenarioStatus.CANCELLED]:
                    break
                    
            # Finalize execution
            if result.status == ScenarioStatus.RUNNING:
                result.status = ScenarioStatus.COMPLETED
                result.end_time = datetime.utcnow()
                result.duration_seconds = (result.end_time - result.start_time).total_seconds()
                
                # Calculate final scores
                await self._calculate_final_scores(result)
                
            # Store results
            self.execution_results[scenario_config.scenario_id] = result
            await self._save_execution_result(result)
            
            # Fire completion event
            await self._fire_event('scenario_completed', {
                'scenario_id': scenario_config.scenario_id,
                'result': result
            })
            
            # Update metrics
            self._update_execution_metrics(result)
            
            logger.info(f"Scenario execution completed: {scenario_config.scenario_id} ({result.status.value})")
            
        except Exception as e:
            logger.error(f"Scenario execution failed: {e}")
            result.status = ScenarioStatus.FAILED
            result.end_time = datetime.utcnow()
            result.error_log.append({
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e),
                'phase': getattr(self, '_current_phase', 'unknown')
            })
            
        finally:
            # Cleanup
            if scenario_config.scenario_id in self.active_scenarios:
                del self.active_scenarios[scenario_config.scenario_id]
                
        return result
        
    async def _execute_phase(
        self,
        scenario_config: ScenarioConfig,
        result: ExecutionResult,
        phase: ExecutionPhase
    ):
        """Execute a specific phase of the scenario"""
        logger.info(f"Executing phase: {phase.value}")
        
        # Update current phase
        if scenario_config.scenario_id in self.active_scenarios:
            self.active_scenarios[scenario_config.scenario_id]['current_phase'] = phase
            
        # Fire phase change event
        await self._fire_event('phase_changed', {
            'scenario_id': scenario_config.scenario_id,
            'phase': phase.value
        })
        
        try:
            if phase == ExecutionPhase.SETUP:
                await self._execute_setup_phase(scenario_config, result)
            elif phase == ExecutionPhase.PREPARATION:
                await self._execute_preparation_phase(scenario_config, result)
            elif phase == ExecutionPhase.COOKING:
                await self._execute_cooking_phase(scenario_config, result)
            elif phase == ExecutionPhase.PLATING:
                await self._execute_plating_phase(scenario_config, result)
            elif phase == ExecutionPhase.SERVICE:
                await self._execute_service_phase(scenario_config, result)
            elif phase == ExecutionPhase.CLEANUP:
                await self._execute_cleanup_phase(scenario_config, result)
                
        except Exception as e:
            logger.error(f"Phase {phase.value} execution failed: {e}")
            result.error_log.append({
                'timestamp': datetime.utcnow().isoformat(),
                'phase': phase.value,
                'error': str(e)
            })
            raise
            
    async def _execute_setup_phase(self, scenario_config: ScenarioConfig, result: ExecutionResult):
        """Execute setup phase - initialize kitchen and agents"""
        # Reset kitchen state
        await self.kitchen_engine.reset_kitchen()
        
        # Get required agents
        agents_needed = min(scenario_config.max_agents, scenario_config.max_concurrent_agents)
        
        # Filter agents by available providers
        available_agents = []
        for agent_id in self.agent_manager.agents.keys():
            agent_context = self.agent_manager.agents[agent_id]
            if agent_context.llm_provider in self.agent_manager.llm_providers:
                available_agents.append(agent_id)
        
        # Take only the number we need
        available_agents = available_agents[:agents_needed]
        
        if len(available_agents) < agents_needed:
            logger.warning(f"Only {len(available_agents)} agents with available providers, needed {agents_needed}")
            if len(available_agents) == 0:
                raise RuntimeError("No agents with available LLM providers found")
            # Use what we have
            agents_needed = len(available_agents)
            
        # Initialize agent contexts for scenario
        for agent_id in available_agents:
            result.agent_performances[agent_id] = {
                'tasks_assigned': 0,
                'tasks_completed': 0,
                'tasks_failed': 0,
                'total_execution_time': 0,
                'total_response_length': 0,
                'communications': [],
                'last_action': None,
                'last_llm_response': '',
                'performance_score': 1.0,
                'stress_level': 0.0,
                'energy_level': 1.0,
                'communications_sent': 0,
                'communications_received': 0
            }
            
        # Save initial kitchen state
        if scenario_config.save_intermediate_states:
            kitchen_state = await self.kitchen_engine.get_kitchen_state()
            result.kitchen_states.append({
                'phase': 'setup',
                'timestamp': datetime.utcnow().isoformat(),
                'state': kitchen_state
            })
            
        logger.info(f"Setup complete: {len(available_agents)} agents assigned")
        
    async def _execute_preparation_phase(self, scenario_config: ScenarioConfig, result: ExecutionResult):
        """Execute preparation phase - prep ingredients and setup stations"""
        # Get recipes for scenario
        recipe_tasks = []
        
        for recipe_id in scenario_config.recipes:
            recipe = self.recipe_manager.recipe_cache.get(recipe_id)
            if recipe:
                # Use the new task generator for prep tasks
                prep_tasks = self.task_generator.generate_prep_tasks(recipe)
                # Convert to task format expected by executor
                for task_data in prep_tasks:
                    recipe_tasks.append({
                        'id': f"prep_{recipe_id}_{len(recipe_tasks)}",
                        'name': task_data['title'],
                        'description': task_data['description'],
                        'agent_type': task_data['agent_type'],
                        'skills_required': task_data['skills_required'],
                        'priority': task_data.get('priority', 'medium'),
                        'estimated_duration': task_data.get('estimated_duration', 10)
                    })
                
        # Execute prep tasks in parallel if enabled
        if scenario_config.parallel_tasks:
            await self._execute_tasks_parallel(recipe_tasks, scenario_config, result)
        else:
            await self._execute_tasks_sequential(recipe_tasks, scenario_config, result)
            
        logger.info(f"Preparation phase complete: {len(recipe_tasks)} tasks executed")
        
    async def _execute_cooking_phase(self, scenario_config: ScenarioConfig, result: ExecutionResult):
        """Execute cooking phase - main cooking tasks"""
        # Generate cooking tasks for all recipes
        cooking_tasks = []
        
        for recipe_id in scenario_config.recipes:
            recipe = self.recipe_manager.recipe_cache.get(recipe_id)
            if recipe:
                # Use the new task generator for cooking tasks
                cook_tasks = self.task_generator.generate_cooking_tasks(recipe)
                # Convert to task format expected by executor
                for task_data in cook_tasks:
                    cooking_tasks.append({
                        'id': f"cook_{recipe_id}_{len(cooking_tasks)}",
                        'name': task_data['title'],
                        'description': task_data['description'],
                        'agent_type': task_data['agent_type'],
                        'skills_required': task_data['skills_required'],
                        'priority': task_data.get('priority', 'medium'),
                        'estimated_duration': task_data.get('estimated_duration', 15)
                    })
                
        # Introduce time pressure if configured
        if scenario_config.time_pressure > 1.0:
            await self._apply_time_pressure(scenario_config, result)
            
        # Randomly trigger crisis events
        if scenario_config.crisis_probability > 0:
            await self._maybe_trigger_crisis(scenario_config, result)
            
        # Execute cooking tasks
        if scenario_config.parallel_tasks:
            await self._execute_tasks_parallel(cooking_tasks, scenario_config, result)
        else:
            await self._execute_tasks_sequential(cooking_tasks, scenario_config, result)
            
        logger.info(f"Cooking phase complete: {len(cooking_tasks)} tasks executed")
        
    async def _execute_plating_phase(self, scenario_config: ScenarioConfig, result: ExecutionResult):
        """Execute plating phase - final presentation"""
        plating_tasks = []
        
        # Create plating tasks for completed recipes
        for recipe_id in scenario_config.recipes:
            task_data = {
                'type': TaskType.PLATE.value,
                'description': f"Plate and present {recipe_id}",
                'priority': 1,
                'recipe_id': recipe_id
            }
            plating_tasks.append(task_data)
            
        # Execute plating tasks
        await self._execute_tasks_sequential(plating_tasks, scenario_config, result)
        
        # Calculate recipe completion
        result.recipes_completed = len(scenario_config.recipes)
        
        logger.info(f"Plating phase complete: {result.recipes_completed} recipes plated")
        
    async def _execute_service_phase(self, scenario_config: ScenarioConfig, result: ExecutionResult):
        """Execute service phase - quality control and service"""
        # Perform quality checks
        quality_scores = []
        
        for recipe_id in scenario_config.recipes:
            # Simulate quality assessment
            base_quality = 0.8
            
            # Adjust based on execution performance
            if result.tasks_failed > 0:
                base_quality -= (result.tasks_failed / max(1, result.tasks_completed)) * 0.3
                
            # Adjust based on time pressure
            if scenario_config.time_pressure > 1.0:
                base_quality -= (scenario_config.time_pressure - 1.0) * 0.2
                
            quality_scores.append(max(0.0, min(1.0, base_quality)))
            
        result.quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        logger.info(f"Service phase complete: quality score = {result.quality_score:.2f}")
        
    async def _execute_cleanup_phase(self, scenario_config: ScenarioConfig, result: ExecutionResult):
        """Execute cleanup phase - kitchen cleanup and reset"""
        cleanup_tasks = [
            {
                'type': TaskType.CLEAN.value,
                'description': 'Clean cooking stations',
                'priority': 1
            },
            {
                'type': TaskType.CLEAN.value,
                'description': 'Clean equipment',
                'priority': 1
            },
            {
                'type': TaskType.CLEAN.value,
                'description': 'Organize ingredients',
                'priority': 2
            }
        ]
        
        # Execute cleanup tasks
        await self._execute_tasks_sequential(cleanup_tasks, scenario_config, result)
        
        # Reset agent states
        await self.agent_manager.cleanup()
        
        logger.info("Cleanup phase complete")
        
    async def _create_prep_tasks(self, recipe: Dict, scenario_config: ScenarioConfig) -> List[Dict]:
        """Create preparation tasks for a recipe"""
        tasks = []
        
        # Ingredient prep tasks
        for ingredient in recipe['ingredients']:
            if ingredient.preparation:
                task_data = {
                    'type': TaskType.PREP.value,
                    'description': f"Prepare {ingredient.name}: {ingredient.preparation}",
                    'priority': 2,
                    'ingredient': ingredient.name,
                    'preparation': ingredient.preparation
                }
                tasks.append(task_data)
                
        # Equipment setup tasks
        for equipment in recipe['equipment']:
            task_data = {
                'type': TaskType.SETUP.value,
                'description': f"Setup {equipment}",
                'priority': 3,
                'equipment': equipment
            }
            tasks.append(task_data)
            
        return tasks
        
    async def _create_cooking_tasks(self, recipe: Dict, scenario_config: ScenarioConfig) -> List[Dict]:
        """Create cooking tasks for a recipe"""
        tasks = []
        
        # Create tasks from recipe instructions
        for step in recipe['instructions']:
            task_data = {
                'type': TaskType.COOK.value,
                'description': step.instruction,
                'priority': 1,
                'duration_minutes': step.duration_minutes,
                'temperature': step.temperature,
                'equipment': step.equipment,
                'techniques': step.techniques
            }
            tasks.append(task_data)
            
        return tasks
        
    async def _execute_tasks_parallel(
        self,
        tasks: List[Dict],
        scenario_config: ScenarioConfig,
        result: ExecutionResult
    ):
        """Execute tasks in true parallel using all available agents"""
        # Get available agents
        available_agents = list(result.agent_performances.keys())
        
        if not available_agents:
            logger.warning("No agents available for task execution")
            return
            
        logger.info(f"🚀 Starting parallel execution of {len(tasks)} tasks with {len(available_agents)} agents")
        
        # Create task batches for better parallel execution
        max_concurrent = min(len(available_agents), 4)  # Limit concurrency for performance
        task_batches = []
        
        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i:i + max_concurrent]
            task_batches.append(batch)
        
        total_completed = 0
        total_failed = 0
        
        # Process each batch in parallel
        for batch_idx, batch in enumerate(task_batches):
            logger.info(f"📦 Processing batch {batch_idx + 1}/{len(task_batches)} ({len(batch)} tasks)")
            
            # Create futures for this batch
            batch_futures = []
            
            for task_idx, task_data in enumerate(batch):
                # Assign agent round-robin within available agents
                agent_id = available_agents[task_idx % len(available_agents)]
                
                # Create task execution coroutine
                future = asyncio.create_task(
                    self._execute_single_task(agent_id, task_data, scenario_config, result),
                    name=f"task_{batch_idx}_{task_idx}"
                )
                batch_futures.append((future, agent_id, task_data))
            
            # Wait for batch completion with timeout
            try:
                # Use timeout to prevent hanging
                completed_tasks = await asyncio.wait_for(
                    asyncio.gather(*[f[0] for f in batch_futures], return_exceptions=True),
                    timeout=30.0  # 30 second timeout per batch
                )
                
                # Process batch results
                for i, (task_result, (future, agent_id, task_data)) in enumerate(zip(completed_tasks, batch_futures)):
                    if isinstance(task_result, Exception):
                        logger.error(f"❌ Task in batch {batch_idx} failed: {task_result}")
                        total_failed += 1
                        result.error_log.append({
                            'timestamp': datetime.utcnow().isoformat(),
                            'batch': batch_idx,
                            'task_index': i,
                            'agent_id': agent_id,
                            'task_description': task_data.get('description', 'Unknown'),
                            'error': str(task_result)
                        })
                    else:
                        total_completed += 1
                        
                logger.info(f"✅ Batch {batch_idx + 1} completed: {len(batch) - sum(1 for r in completed_tasks if isinstance(r, Exception))}/{len(batch)} tasks successful")
                
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Batch {batch_idx + 1} timed out, cancelling remaining tasks")
                for future, agent_id, task_data in batch_futures:
                    if not future.done():
                        future.cancel()
                total_failed += len([f for f, _, _ in batch_futures if not f.done()])
            
            # Small delay between batches to prevent overwhelming
            if batch_idx < len(task_batches) - 1:
                await asyncio.sleep(0.1)
        
        # Update final results
        result.tasks_completed += total_completed
        result.tasks_failed += total_failed
        
        logger.info(f"🎯 Parallel execution complete: {total_completed} completed, {total_failed} failed")
        
        # Log agent performance summary
        for agent_id, perf in result.agent_performances.items():
            if perf['tasks_completed'] > 0:
                avg_time = perf.get('total_execution_time', 0) / perf['tasks_completed']
                with self.db_manager.get_session() as session:
                    db_agent = session.query(Agent).filter(Agent.id == agent_id).first()
                    agent_name = db_agent.name if db_agent else f"Agent {agent_id}"
                logger.info(f"👨‍🍳 {agent_name}: {perf['tasks_completed']} tasks, avg {avg_time:.1f}s, last: {perf.get('last_action', 'N/A')}")
                result.tasks_completed += 1
                
    async def _execute_tasks_sequential(
        self,
        tasks: List[Dict],
        scenario_config: ScenarioConfig,
        result: ExecutionResult
    ):
        """Execute tasks sequentially"""
        available_agents = list(result.agent_performances.keys())
        
        if not available_agents:
            logger.warning("No agents available for task execution")
            return
            
        for i, task_data in enumerate(tasks):
            # Assign agent round-robin
            agent_id = available_agents[i % len(available_agents)]
            
            try:
                await self._execute_single_task(agent_id, task_data, scenario_config, result)
                result.tasks_completed += 1
            except Exception as e:
                logger.error(f"Task {i} failed: {e}")
                result.tasks_failed += 1
                result.error_log.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'task_index': i,
                    'error': str(e)
                })
                
    async def _execute_single_task(
        self,
        agent_id: str,
        task_data: Dict,
        scenario_config: ScenarioConfig,
        result: ExecutionResult
    ):
        """Execute a single task with an agent and track completion"""
        start_time = datetime.utcnow()
        
        # Create and assign task to agent
        task_id = await self.agent_manager.assign_task(agent_id, task_data)
        
        # Update agent performance tracking
        if agent_id in result.agent_performances:
            result.agent_performances[agent_id]['tasks_assigned'] += 1
            
        try:
            # Get agent info for better context
            with self.db_manager.get_session() as session:
                db_agent = session.query(Agent).filter(Agent.id == agent_id).first()
                agent_name = db_agent.name if db_agent else f"Agent {agent_id}"
            
            logger.info(f"🔄 {agent_name} starting task: {task_data.get('description', 'Unknown task')}")
            
            # Enhanced context for better LLM responses
            context = {
                'current_task': task_data['description'],
                'task_type': task_data.get('type', 'general'),
                'kitchen_state': await self.kitchen_engine.get_kitchen_state(),
                'scenario_id': scenario_config.scenario_id,
                'urgency': task_data.get('urgency', 'medium'),
                'expected_duration': task_data.get('duration_minutes', 5),
                'equipment_needed': task_data.get('equipment', []),
                'ingredients_needed': task_data.get('ingredients', [])
            }
            
            # Execute agent action with improved tracking
            action_start_time = time.time()
            action_result = await self.agent_manager.execute_agent_action(agent_id, context)
            action_end_time = time.time()
            response_time = action_end_time - action_start_time
            
            # Track response time in result
            if self.current_result:
                self.current_result.record_response_time(response_time)
                self.current_result.record_message()  # Track communication
            
            # Mark task as completed in database
            with self.db_manager.get_session() as session:
                task = session.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.status = TaskStatus.COMPLETED.value
                    task.completed_at = datetime.utcnow()
                    task.result = {
                        'quality_score': action_result.get('quality_score', 0.8),
                        'execution_time': (datetime.utcnow() - start_time).total_seconds(),
                        'response_time': response_time,
                        'llm_response': action_result.get('llm_response', ''),
                        'action_taken': action_result.get('action', 'completed'),
                        'agent_name': agent_name
                    }
                    session.commit()
                    
                    # Log task completion with details
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    logger.info(f"✅ {agent_name} completed task in {duration:.1f}s: {action_result.get('action', 'Unknown action')}")
            
            # Update performance with detailed metrics
            result.agent_performances[agent_id]['tasks_completed'] += 1
            result.agent_performances[agent_id]['total_execution_time'] += (datetime.utcnow() - start_time).total_seconds()
            result.agent_performances[agent_id]['last_action'] = action_result.get('action', 'Unknown')
            result.agent_performances[agent_id]['last_llm_response'] = action_result.get('llm_response', '')[:100] + "..." if len(action_result.get('llm_response', '')) > 100 else action_result.get('llm_response', '')
            
            # Fire task completion event
            await self._fire_event('task_completed', {
                'scenario_id': scenario_config.scenario_id,
                'agent_id': agent_id,
                'agent_name': agent_name,
                'task_id': task_id,
                'task_description': task_data['description'],
                'action_result': action_result,
                'execution_time': (datetime.utcnow() - start_time).total_seconds()
            })
            
            return action_result
            
        except Exception as e:
            # Mark task as failed
            with self.db_manager.get_session() as session:
                task = session.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.status = TaskStatus.FAILED.value
                    task.completed_at = datetime.utcnow()
                    task.result = {
                        'error': str(e),
                        'execution_time': (datetime.utcnow() - start_time).total_seconds()
                    }
                    session.commit()
            
            result.agent_performances[agent_id]['tasks_failed'] += 1
            logger.error(f"❌ Task failed for {agent_name}: {str(e)}")
            raise
            
    async def _apply_time_pressure(self, scenario_config: ScenarioConfig, result: ExecutionResult):
        """Apply time pressure to the scenario"""
        # Increase stress levels for all agents
        for agent_id in result.agent_performances:
            if agent_id in self.agent_manager.agents:
                agent = self.agent_manager.agents[agent_id]
                agent.stress_level = min(1.0, agent.stress_level + 0.1)
                
        logger.info("⏰ Applied time pressure to all agents")
        
    def _track_communication_pattern(
        self, 
        agent_id: int, 
        agent_name: str, 
        task_description: str, 
        llm_response: str, 
        result: ExecutionResult
    ):
        """Track communication patterns between agents and identify collaboration"""
        # Initialize communication tracking if not exists
        if 'communication_patterns' not in result.metrics:
            result.metrics['communication_patterns'] = {
                'agent_interactions': {},
                'collaboration_score': 0.0,
                'response_similarity': {},
                'task_handoffs': []
            }
        
        patterns = result.metrics['communication_patterns']
        
        # Track agent interaction frequency
        if agent_id not in patterns['agent_interactions']:
            patterns['agent_interactions'][agent_id] = {
                'agent_name': agent_name,
                'total_tasks': 0,
                'response_keywords': {},
                'collaboration_mentions': 0,
                'avg_response_length': 0,
                'total_response_length': 0
            }
        
        interaction = patterns['agent_interactions'][agent_id]
        interaction['total_tasks'] += 1
        
        if llm_response:
            response_length = len(llm_response)
            interaction['total_response_length'] += response_length
            interaction['avg_response_length'] = interaction['total_response_length'] / interaction['total_tasks']
            
            # Extract keywords and collaboration indicators
            response_lower = llm_response.lower()
            
            # Count collaboration keywords
            collaboration_keywords = ['help', 'assist', 'collaborate', 'together', 'team', 'coordinate', 'support']
            collaboration_count = sum(1 for keyword in collaboration_keywords if keyword in response_lower)
            interaction['collaboration_mentions'] += collaboration_count
            
            # Track common cooking keywords
            cooking_keywords = ['cook', 'prepare', 'chop', 'heat', 'season', 'serve', 'plate', 'garnish', 'sauce', 'ingredient']
            for keyword in cooking_keywords:
                if keyword in response_lower:
                    if keyword not in interaction['response_keywords']:
                        interaction['response_keywords'][keyword] = 0
                    interaction['response_keywords'][keyword] += 1
            
            # Check for task handoffs (mentions of other agents or roles)
            handoff_indicators = ['chef', 'sous', 'prep', 'station', 'pass', 'expedite', 'coordinate']
            for indicator in handoff_indicators:
                if indicator in response_lower and indicator not in agent_name.lower():
                    patterns['task_handoffs'].append({
                        'from_agent': agent_name,
                        'from_agent_id': agent_id,
                        'task': task_description,
                        'indicator': indicator,
                        'timestamp': datetime.utcnow().isoformat()
                    })
        
        # Calculate overall collaboration score
        total_agents = len(patterns['agent_interactions'])
        if total_agents > 1:
            collaboration_sum = sum(
                agent_data['collaboration_mentions'] 
                for agent_data in patterns['agent_interactions'].values()
            )
            total_tasks = sum(
                agent_data['total_tasks'] 
                for agent_data in patterns['agent_interactions'].values()
            )
            patterns['collaboration_score'] = collaboration_sum / max(total_tasks, 1)
        
        # Log significant collaboration events
        if llm_response and len(llm_response) > 100:
            response_lower = llm_response.lower()
            if any(keyword in response_lower for keyword in ['help', 'assist', 'collaborate', 'coordinate']):
                logger.info(f"🤝 {agent_name} showed collaboration in response: {llm_response[:80]}...")
        
        # Track response similarity for coordination analysis
        if len(patterns['agent_interactions']) > 1:
            self._analyze_response_similarity(agent_id, llm_response, patterns)
    
    def _analyze_response_similarity(self, agent_id: int, llm_response: str, patterns: Dict):
        """Analyze response similarity between agents to detect coordination"""
        if not llm_response:
            return
            
        # Simple keyword-based similarity analysis
        response_words = set(llm_response.lower().split())
        
        similarity_key = f"agent_{agent_id}"
        if similarity_key not in patterns['response_similarity']:
            patterns['response_similarity'][similarity_key] = {
                'common_words': set(),
                'unique_words': set(),
                'similarity_scores': {}
            }
        
        current_agent_data = patterns['response_similarity'][similarity_key]
        current_agent_data['common_words'].update(response_words)
        
        # Compare with other agents
        for other_agent_key, other_agent_data in patterns['response_similarity'].items():
            if other_agent_key != similarity_key and other_agent_data['common_words']:
                # Calculate Jaccard similarity
                intersection = len(current_agent_data['common_words'] & other_agent_data['common_words'])
                union = len(current_agent_data['common_words'] | other_agent_data['common_words'])
                similarity = intersection / union if union > 0 else 0
                
                current_agent_data['similarity_scores'][other_agent_key] = similarity
                
                # Log high similarity (potential coordination)
                if similarity > 0.3:  # 30% similarity threshold
                    logger.info(f"🔗 High similarity ({similarity:.2f}) between agents in responses - potential coordination")
    
    async def _fire_event(self, event_type: str, event_data: Dict):
        """Fire events for scenario execution (placeholder for future event system)"""
        # This is a placeholder for a future event system
        # Could be used for real-time monitoring, notifications, etc.
        logger.debug(f"Event fired: {event_type} - {event_data.get('agent_name', 'Unknown')} - {event_data.get('task_description', 'Unknown task')[:50]}...")
        
        # Store event in metrics for analysis
        if hasattr(self, 'current_result') and self.current_result:
            if 'events' not in self.current_result.metrics:
                self.current_result.metrics['events'] = []
            
            self.current_result.metrics['events'].append({
                'type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'data': event_data
            })
    
    async def _maybe_trigger_crisis(self, scenario_config: ScenarioConfig, result: ExecutionResult):
        """Maybe trigger a crisis event based on probability"""
        import random
        
        if random.random() < scenario_config.crisis_probability:
            crisis_types = ['equipment_failure', 'ingredient_shortage', 'time_pressure']
            crisis_type = random.choice(crisis_types)
            
            crisis_context = {
                'scenario_id': scenario_config.scenario_id,
                'crisis_type': crisis_type,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Handle crisis with agent manager
            crisis_responses = await self.agent_manager.handle_crisis(crisis_type, crisis_context)
            
            # Record crisis event
            result.crisis_events.append({
                'type': crisis_type,
                'timestamp': crisis_context['timestamp'],
                'responses': crisis_responses
            })
            
            # Fire crisis event
            await self._fire_event('crisis_occurred', {
                'scenario_id': scenario_config.scenario_id,
                'crisis_type': crisis_type,
                'responses': crisis_responses
            })
            
            logger.warning(f"Crisis triggered: {crisis_type}")
            
    async def _calculate_final_scores(self, result: ExecutionResult):
        """Calculate final performance scores"""
        # Efficiency score based on task completion
        total_tasks = result.tasks_completed + result.tasks_failed
        if total_tasks > 0:
            result.efficiency_score = result.tasks_completed / total_tasks
        else:
            result.efficiency_score = 0.0
            
        # Collaboration score based on communications
        total_communications = len(result.communications)
        agent_count = len(result.agent_performances)
        
        if agent_count > 1:
            expected_communications = agent_count * (agent_count - 1) * 2  # Minimum expected
            result.collaboration_score = min(1.0, total_communications / expected_communications)
        else:
            result.collaboration_score = 1.0  # Single agent scenarios
            
        logger.info(f"Final scores - Quality: {result.quality_score:.2f}, "
                   f"Efficiency: {result.efficiency_score:.2f}, "
                   f"Collaboration: {result.collaboration_score:.2f}")
                   
    async def _save_execution_result(self, result: ExecutionResult):
        """Save execution result to database"""
        try:
            # Log the completion 
            logger.info(f"Scenario {result.scenario_id} completed with status {result.status}")
            logger.info(f"Tasks: {result.tasks_completed} completed, {result.tasks_failed} failed")
            logger.info(f"Quality: {result.quality_score:.2f}, Efficiency: {result.efficiency_score:.2f}")
            
            # Save metrics to database
            with self.db_manager.get_session() as session:
                # Get current agent and task counts
                total_agents = session.query(Agent).count()
                active_agents = len([a for a in self.agent_manager.agents.values() 
                                   if a.status in [AgentStatus.BUSY, AgentStatus.COLLABORATING]])
                total_tasks = session.query(Task).count()
                completed_tasks = session.query(Task).filter(Task.status == 'completed').count()
                
                # Calculate average metrics from recent tasks 
                recent_actions = session.query(AgentAction).filter(
                    AgentAction.created_at >= result.start_time
                ).all()
                
                avg_quality = result.quality_score
                avg_coordination = result.collaboration_score
                
                # Build detailed metrics
                agent_metrics = {}
                for agent_id, agent_context in self.agent_manager.agents.items():
                    agent_actions = [a for a in recent_actions if a.agent_id == agent_id]
                    agent_metrics[str(agent_id)] = {
                        'name': agent_context.name,
                        'type': agent_context.agent_type.value,
                        'provider': agent_context.llm_provider,
                        'actions_count': len(agent_actions),
                        'status': agent_context.status.value
                    }
                
                task_metrics = {
                    'scenario_id': result.scenario_id,
                    'scenario_type': result.scenario_type,  # Now stored in result
                    'duration_seconds': result.duration_seconds,
                    'tasks_completed': result.tasks_completed,
                    'tasks_failed': result.tasks_failed,
                    'recipes_completed': result.recipes_completed
                }
                
                system_metrics = {
                    'execution_time': result.duration_seconds,
                    'quality_score': result.quality_score,
                    'efficiency_score': result.efficiency_score,
                    'collaboration_score': result.collaboration_score,
                    'llm_providers_used': list(set([a.llm_provider for a in self.agent_manager.agents.values()])),
                    'total_llm_responses': len(recent_actions)
                }
                
                # Create metrics snapshot
                metrics = MetricsSnapshot(
                    total_agents=total_agents,
                    active_agents=active_agents,
                    total_tasks=total_tasks,
                    completed_tasks=completed_tasks,
                    avg_task_completion_time=result.duration_seconds / max(result.tasks_completed, 1),
                    avg_quality_score=avg_quality,
                    avg_coordination_score=avg_coordination,
                    messages_sent=result.messages_sent,  # Now tracked in result
                    avg_response_time=result.get_avg_response_time(),  # Now tracked in result
                    agent_metrics=agent_metrics,
                    task_metrics=task_metrics,
                    system_metrics=system_metrics,
                    period_start=result.start_time,
                    period_end=result.end_time
                )
                
                session.add(metrics)
                session.commit()
                
                logger.info(f"Saved metrics snapshot for scenario {result.scenario_id}")
                
        except Exception as e:
            logger.error(f"Failed to save execution result: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
    def _update_execution_metrics(self, result: ExecutionResult):
        """Update overall execution metrics"""
        self.execution_metrics['total_scenarios'] += 1
        
        if result.status == ScenarioStatus.COMPLETED:
            self.execution_metrics['successful_scenarios'] += 1
        else:
            self.execution_metrics['failed_scenarios'] += 1
            
        # Update averages
        total = self.execution_metrics['total_scenarios']
        self.execution_metrics['average_duration'] = (
            (self.execution_metrics['average_duration'] * (total - 1) + result.duration_seconds) / total
        )
        self.execution_metrics['average_quality'] = (
            (self.execution_metrics['average_quality'] * (total - 1) + result.quality_score) / total
        )
        self.execution_metrics['average_efficiency'] = (
            (self.execution_metrics['average_efficiency'] * (total - 1) + result.efficiency_score) / total
        )
        
    async def _fire_event(self, event_type: str, data: Dict):
        """Fire event to registered handlers"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"Event handler failed for {event_type}: {e}")
                    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        
    async def execute_multiple_scenarios(
        self,
        scenario_configs: List[ScenarioConfig],
        parallel: bool = True
    ) -> List[ExecutionResult]:
        """Execute multiple scenarios"""
        if parallel:
            # Execute scenarios in parallel
            futures = [
                asyncio.create_task(self.execute_scenario(config))
                for config in scenario_configs
            ]
            
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            # Filter out exceptions
            valid_results = [
                result for result in results
                if isinstance(result, ExecutionResult)
            ]
            
            return valid_results
        else:
            # Execute scenarios sequentially
            results = []
            for config in scenario_configs:
                result = await self.execute_scenario(config)
                results.append(result)
                
            return results
            
    def get_execution_summary(self) -> Dict:
        """Get summary of all executions"""
        return {
            'metrics': self.execution_metrics,
            'active_scenarios': len(self.active_scenarios),
            'completed_scenarios': len(self.execution_results),
            'recent_results': [
                {
                    'scenario_id': result.scenario_id,
                    'status': result.status.value if isinstance(result.status, ScenarioStatus) else result.status,
                    'duration': result.duration_seconds,
                    'quality_score': result.quality_score,
                    'efficiency_score': result.efficiency_score
                }
                for result in list(self.execution_results.values())[-10:]  # Last 10 results
            ]
        }
        
    async def cleanup(self):
        """Cleanup executor resources"""
        # Cancel active scenarios
        for scenario_id in list(self.active_scenarios.keys()):
            if scenario_id in self.execution_results:
                result = self.execution_results[scenario_id]
                result.status = ScenarioStatus.CANCELLED
                
        self.active_scenarios.clear()
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True)
        
        logger.info("Scenario executor cleaned up")