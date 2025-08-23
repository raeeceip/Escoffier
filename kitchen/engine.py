"""
Kitchen simulation engine with advanced state management and realistic physics.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import random
import logging
from datetime import datetime, timedelta
import json

from database.models import (
    Agent, Task, Ingredient, Recipe, AgentAction, Communication,
    KitchenRole, KitchenLocation, TaskStatus, MessageType
)
from database import Database, get_database
from config import Settings, get_settings

logger = logging.getLogger(__name__)


class KitchenState(Enum):
    """Overall kitchen operation states."""
    IDLE = "idle"
    PREP = "prep"
    SERVICE = "service"
    RUSH = "rush"
    CRISIS = "crisis"
    CLEANUP = "cleanup"


@dataclass
class Equipment:
    """Kitchen equipment with state and availability."""
    name: str
    location: KitchenLocation
    is_available: bool = True
    condition: float = 1.0  # 0-1, 1 = perfect condition
    temperature: Optional[float] = None
    in_use_by: Optional[int] = None  # Agent ID
    maintenance_required: bool = False


@dataclass
class KitchenStation:
    """A kitchen workstation with equipment and capacity."""
    name: str
    location: KitchenLocation
    equipment: List[Equipment] = field(default_factory=list)
    max_capacity: int = 2  # Number of agents that can work here
    current_agents: Set[int] = field(default_factory=set)
    cleanliness: float = 1.0  # 0-1
    temperature: float = 20.0  # Celsius
    
    @property
    def available_capacity(self) -> int:
        return max(0, self.max_capacity - len(self.current_agents))
    
    @property
    def is_full(self) -> bool:
        return len(self.current_agents) >= self.max_capacity


@dataclass
class EnvironmentalConditions:
    """Kitchen environmental conditions affecting performance."""
    temperature: float = 22.0  # Celsius
    humidity: float = 60.0  # Percentage
    noise_level: float = 0.5  # 0-1
    rush_multiplier: float = 1.0  # Service rush intensity
    time_pressure: float = 0.0  # 0-1
    crisis_active: bool = False
    crisis_type: Optional[str] = None


class KitchenEngine:
    """Advanced kitchen simulation engine."""
    
    def __init__(self, database: Optional[Database] = None, settings: Optional[Settings] = None):
        self.db = database or get_database()
        self.settings = settings or get_settings()
        
        # Kitchen state
        self.state = KitchenState.IDLE
        self.conditions = EnvironmentalConditions()
        self.stations: Dict[KitchenLocation, KitchenStation] = {}
        self.global_inventory: Dict[str, float] = {}
        
        # Simulation control
        self.is_running = False
        self.simulation_speed = 1.0  # Default simulation speed
        self.tick_rate = 1.0  # Seconds between simulation ticks
        
        # Metrics tracking
        self.metrics = {
            "total_tasks_completed": 0,
            "average_completion_time": 0.0,
            "coordination_events": 0,
            "crisis_events": 0,
            "quality_incidents": 0,
            "communication_volume": 0
        }
        
        self._initialize_stations()
        self._initialize_equipment()
        
        logger.info("Kitchen engine initialized")
    
    def _initialize_stations(self):
        """Initialize kitchen stations with realistic configurations."""
        station_configs = {
            KitchenLocation.PREP: {
                "name": "Prep Station",
                "max_capacity": 3,
                "equipment_names": ["cutting_board", "prep_knives", "food_processor"]
            },
            KitchenLocation.GRILL: {
                "name": "Grill Station", 
                "max_capacity": 2,
                "equipment_names": ["gas_grill", "grill_tools", "thermometer"]
            },
            KitchenLocation.SAUTE: {
                "name": "Sauté Station",
                "max_capacity": 2,
                "equipment_names": ["gas_burners", "saute_pans", "sauce_pots"]
            },
            KitchenLocation.BAKING: {
                "name": "Baking Station",
                "max_capacity": 2,
                "equipment_names": ["convection_oven", "mixers", "baking_tools"]
            },
            KitchenLocation.COLD_PREP: {
                "name": "Cold Prep",
                "max_capacity": 2,
                "equipment_names": ["refrigeration", "salad_station", "cold_tools"]
            },
            KitchenLocation.EXPEDITE: {
                "name": "Expedite Station",
                "max_capacity": 1,
                "equipment_names": ["heat_lamps", "plating_station", "garnish_station"]
            },
            KitchenLocation.DISH: {
                "name": "Dish Station",
                "max_capacity": 2,
                "equipment_names": ["dishwasher", "sanitizer", "drying_racks"]
            }
        }
        
        for location, config in station_configs.items():
            station = KitchenStation(
                name=config["name"],
                location=location,
                max_capacity=config["max_capacity"]
            )
            
            # Add equipment to station
            for equipment_name in config["equipment_names"]:
                equipment = Equipment(
                    name=equipment_name,
                    location=location,
                    condition=random.uniform(0.8, 1.0)
                )
                station.equipment.append(equipment)
            
            self.stations[location] = station
    
    def _initialize_equipment(self):
        """Initialize specialized equipment with realistic properties."""
        # Temperature-controlled equipment
        for station in self.stations.values():
            for equipment in station.equipment:
                if "oven" in equipment.name:
                    equipment.temperature = random.uniform(180, 220)
                elif "grill" in equipment.name:
                    equipment.temperature = random.uniform(200, 300)
                elif "refriger" in equipment.name:
                    equipment.temperature = random.uniform(2, 4)
    
    async def start_simulation(self):
        """Start the kitchen simulation loop."""
        if self.is_running:
            logger.warning("Simulation is already running")
            return
        
        self.is_running = True
        logger.info("Kitchen simulation started")
        
        try:
            while self.is_running:
                await self._simulation_tick()
                await asyncio.sleep(self.tick_rate / self.simulation_speed)
        except Exception as e:
            logger.error(f"Simulation error: {e}")
        finally:
            self.is_running = False
            logger.info("Kitchen simulation stopped")
    
    def stop_simulation(self):
        """Stop the kitchen simulation."""
        self.is_running = False
    
    async def _simulation_tick(self):
        """Execute one simulation tick."""
        try:
            # Update environmental conditions
            await self._update_environment()
            
            # Process agent actions
            await self._process_agent_actions()
            
            # Update equipment states
            await self._update_equipment()
            
            # Handle crisis events
            await self._handle_crisis_events()
            
            # Update metrics
            await self._update_metrics()
            
        except Exception as e:
            logger.error(f"Simulation tick error: {e}")
    
    async def _update_environment(self):
        """Update environmental conditions based on kitchen activity."""
        # Simulate temperature changes based on equipment usage
        active_heat_sources = sum(
            1 for station in self.stations.values()
            for equipment in station.equipment
            if equipment.in_use_by and ("oven" in equipment.name or "grill" in equipment.name)
        )
        
        # Temperature increases with active cooking
        base_temp = 22.0
        temp_increase = active_heat_sources * 2.0
        self.conditions.temperature = min(35.0, base_temp + temp_increase)
        
        # Humidity increases with steam and cooking
        steam_sources = sum(
            1 for station in self.stations.values()
            for equipment in station.equipment
            if equipment.in_use_by and ("burner" in equipment.name or "pot" in equipment.name)
        )
        self.conditions.humidity = min(80.0, 60.0 + steam_sources * 3.0)
        
        # Noise level based on activity
        total_agents = sum(len(station.current_agents) for station in self.stations.values())
        self.conditions.noise_level = min(1.0, total_agents * 0.1)
        
        # Update kitchen state based on activity level
        if total_agents == 0:
            self.state = KitchenState.IDLE
        elif total_agents <= 3:
            self.state = KitchenState.PREP
        elif total_agents <= 6:
            self.state = KitchenState.SERVICE
        else:
            self.state = KitchenState.RUSH
            self.conditions.rush_multiplier = 1.0 + (total_agents - 6) * 0.2
    
    async def _process_agent_actions(self):
        """Process actions from all active agents."""
        with self.db.session_scope() as session:
            # Get all active agents
            active_agents = session.query(Agent).filter(Agent.is_active == True).all()
            
            for agent in active_agents:
                await self._process_agent_tick(agent, session)
    
    async def _process_agent_tick(self, agent: Agent, session):
        """Process one tick for a specific agent."""
        try:
            # Update agent stress based on environment
            stress_factors = [
                self.conditions.temperature > 30.0,  # Hot kitchen
                self.conditions.noise_level > 0.7,   # Noisy
                self.state == KitchenState.RUSH,     # Rush period
                self.conditions.crisis_active        # Crisis situation
            ]
            
            stress_increase = sum(stress_factors) * 0.1
            agent.stress_level = min(1.0, agent.stress_level + stress_increase)
            
            # Stress naturally decreases over time
            if not stress_factors:
                agent.stress_level = max(0.0, agent.stress_level - 0.05)
            
            # Update agent location based on current tasks
            current_task = session.query(Task).filter(
                Task.agent_id == agent.id,
                Task.status == TaskStatus.IN_PROGRESS
            ).first()
            
            if current_task:
                # Determine location based on task type
                task_locations = {
                    "prep": KitchenLocation.PREP,
                    "grill": KitchenLocation.GRILL,
                    "saute": KitchenLocation.SAUTE,
                    "bake": KitchenLocation.BAKING,
                    "plate": KitchenLocation.EXPEDITE,
                    "clean": KitchenLocation.DISH
                }
                
                for task_type, location in task_locations.items():
                    if task_type in current_task.task_type.lower():
                        await self._move_agent_to_station(agent, location, session)
                        break
        
        except Exception as e:
            logger.error(f"Error processing agent {agent.id}: {e}")
    
    async def _move_agent_to_station(self, agent: Agent, target_location: KitchenLocation, session):
        """Move agent to a specific station if possible."""
        # Remove from current station
        if agent.current_location:
            current_station = self.stations.get(agent.current_location)
            if current_station and agent.id in current_station.current_agents:
                current_station.current_agents.remove(agent.id)
        
        # Try to add to target station
        target_station = self.stations.get(target_location)
        if target_station and not target_station.is_full:
            target_station.current_agents.add(agent.id)
            agent.current_location = target_location
            
            # Create movement action
            action = AgentAction(
                agent_id=agent.id,
                action_type="move",
                description=f"Moved to {target_station.name}",
                location=target_location,
                duration=5,  # 5 seconds to move
                success=True
            )
            session.add(action)
    
    async def _update_equipment(self):
        """Update equipment states and conditions."""
        for station in self.stations.values():
            for equipment in station.equipment:
                # Equipment degrades slowly over time
                if equipment.in_use_by:
                    equipment.condition = max(0.0, equipment.condition - 0.001)
                    
                    # Chance of breakdown based on condition
                    if equipment.condition < 0.3 and random.random() < 0.01:
                        equipment.is_available = False
                        equipment.maintenance_required = True
                        logger.warning(f"Equipment breakdown: {equipment.name} at {station.name}")
                
                # Station cleanliness decreases with use
                if len(station.current_agents) > 0:
                    station.cleanliness = max(0.0, station.cleanliness - 0.002)
    
    async def _handle_crisis_events(self):
        """Handle random crisis events to test agent coordination."""
        # Crisis events are always enabled for now
        # if not self.settings.kitchen.enable_crisis_events:
        #     return
        
        # Only trigger crisis if not already in one
        if self.conditions.crisis_active:
            # Resolve crisis after some time
            if random.random() < 0.1:  # 10% chance to resolve each tick
                self.conditions.crisis_active = False
                self.conditions.crisis_type = None
                logger.info("Crisis resolved")
            return
        
        # Small chance of crisis during busy periods
        if self.state in [KitchenState.SERVICE, KitchenState.RUSH] and random.random() < 0.005:
            crisis_types = [
                "equipment_failure",
                "ingredient_shortage", 
                "large_order",
                "staff_injury",
                "food_safety_issue"
            ]
            
            crisis_type = random.choice(crisis_types)
            self.conditions.crisis_active = True
            self.conditions.crisis_type = crisis_type
            self.metrics["crisis_events"] += 1
            
            logger.warning(f"Crisis event triggered: {crisis_type}")
            
            # Create crisis tasks for agents to handle
            await self._create_crisis_tasks(crisis_type)
    
    async def _create_crisis_tasks(self, crisis_type: str):
        """Create emergency tasks to handle crisis situations."""
        with self.db.session_scope() as session:
            if crisis_type == "equipment_failure":
                # Find broken equipment and create repair task
                for station in self.stations.values():
                    broken_equipment = [e for e in station.equipment if e.maintenance_required]
                    if broken_equipment:
                        equipment = broken_equipment[0]
                        task = Task(
                            task_type="emergency_repair",
                            description=f"Emergency repair of {equipment.name}",
                            priority=10,  # Highest priority
                            status=TaskStatus.PENDING.value,
                            estimated_duration=15,
                            parameters={"equipment": equipment.name, "location": station.location.value}
                        )
                        session.add(task)
                        break
            
            elif crisis_type == "ingredient_shortage":
                # Create emergency restocking task
                task = Task(
                    task_type="emergency_restock",
                    description="Emergency ingredient restocking",
                    priority=9,
                    status=TaskStatus.PENDING.value,
                    estimated_duration=10,
                    parameters={"urgency": "high"}
                )
                session.add(task)
    
    async def _update_metrics(self):
        """Update simulation metrics."""
        with self.db.session_scope() as session:
            # Count completed tasks in the last minute
            one_minute_ago = datetime.now() - timedelta(minutes=1)
            recent_completed = session.query(Task).filter(
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= one_minute_ago
            ).count()
            
            if recent_completed > 0:
                self.metrics["total_tasks_completed"] += recent_completed
            
            # Count recent communications
            recent_comms = session.query(Communication).filter(
                Communication.created_at >= one_minute_ago
            ).count()
            
            self.metrics["communication_volume"] += recent_comms
    
    def get_station_status(self, location: KitchenLocation) -> Dict[str, Any]:
        """Get detailed status of a specific station."""
        station = self.stations.get(location)
        if not station:
            return {}
        
        return {
            "name": station.name,
            "location": location.value,
            "current_agents": list(station.current_agents),
            "capacity": f"{len(station.current_agents)}/{station.max_capacity}",
            "available_capacity": station.available_capacity,
            "cleanliness": round(station.cleanliness, 2),
            "temperature": round(station.temperature, 1),
            "equipment": [
                {
                    "name": eq.name,
                    "available": eq.is_available,
                    "condition": round(eq.condition, 2),
                    "in_use": eq.in_use_by is not None,
                    "maintenance_required": eq.maintenance_required
                }
                for eq in station.equipment
            ]
        }
    
    def get_kitchen_status(self) -> Dict[str, Any]:
        """Get overall kitchen status."""
        total_agents = sum(len(station.current_agents) for station in self.stations.values())
        
        return {
            "state": self.state.value,
            "total_agents_active": total_agents,
            "environmental_conditions": {
                "temperature": round(self.conditions.temperature, 1),
                "humidity": round(self.conditions.humidity, 1),
                "noise_level": round(self.conditions.noise_level, 2),
                "rush_multiplier": round(self.conditions.rush_multiplier, 2),
                "time_pressure": round(self.conditions.time_pressure, 2)
            },
            "crisis": {
                "active": self.conditions.crisis_active,
                "type": self.conditions.crisis_type
            },
            "stations": {
                location.value: self.get_station_status(location)
                for location in self.stations.keys()
            },
            "metrics": self.metrics.copy()
        }
    
    async def assign_agent_to_task(self, agent_id: int, task_id: int) -> bool:
        """Assign an agent to a specific task."""
        with self.db.session_scope() as session:
            agent = session.query(Agent).filter(Agent.id == agent_id).first()
            task = session.query(Task).filter(Task.id == task_id).first()
            
            if not agent or not task:
                return False
            
            if task.status != TaskStatus.PENDING:
                return False
            
            # Check if agent has required skills (simplified)
            task.agent_id = agent_id
            task.status = TaskStatus.IN_PROGRESS
            task.assigned_at = datetime.now()
            task.started_at = datetime.now()
            
            logger.info(f"Agent {agent_id} assigned to task {task_id}")
            return True
    
    async def complete_task(self, task_id: int, quality_score: float = 0.8) -> bool:
        """Mark a task as completed."""
        with self.db.session_scope() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            
            if not task or task.status != TaskStatus.IN_PROGRESS:
                return False
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            if task.started_at:
                duration = (task.completed_at - task.started_at).total_seconds() / 60
                task.actual_duration = int(duration)
            
            task.actual_quality = {"overall_score": quality_score}
            
            logger.info(f"Task {task_id} completed with quality score {quality_score}")
            return True
    
    async def reset_kitchen(self):
        """Reset kitchen to initial state for scenario execution."""
        logger.info("Resetting kitchen state for new scenario")
        
        # Reset kitchen state
        self.state = KitchenState.IDLE
        self.conditions = EnvironmentalConditions()
        
        # Clear all agents from stations
        for station in self.stations.values():
            station.current_agents.clear()
            station.cleanliness = 1.0
            station.temperature = 20.0
        
        # Reset equipment states
        for station in self.stations.values():
            for equipment in station.equipment:
                equipment.is_available = True
                equipment.condition = random.uniform(0.8, 1.0)
                equipment.in_use_by = None
                equipment.maintenance_required = False
                
                # Reset temperatures for temperature-controlled equipment
                if "oven" in equipment.name:
                    equipment.temperature = random.uniform(180, 220)
                elif "grill" in equipment.name:
                    equipment.temperature = random.uniform(200, 300)
                elif "refriger" in equipment.name:
                    equipment.temperature = random.uniform(2, 4)
        
        # Reset inventory to full levels
        self.global_inventory = {
            "flour": 100.0,
            "eggs": 50.0,
            "milk": 20.0,
            "butter": 10.0,
            "salt": 5.0,
            "pepper": 2.0,
            "oil": 15.0,
            "onions": 25.0,
            "garlic": 10.0,
            "tomatoes": 30.0,
            "beef": 20.0,
            "chicken": 25.0,
            "fish": 15.0
        }
        
        # Reset metrics
        self.metrics = {
            "total_tasks_completed": 0,
            "average_completion_time": 0.0,
            "coordination_events": 0,
            "crisis_events": 0,
            "quality_incidents": 0,
            "communication_volume": 0
        }
        
        logger.info("Kitchen reset complete")
    
    async def get_kitchen_state(self) -> Dict[str, Any]:
        """Get current kitchen state for scenario execution."""
        return {
            "state": self.state.value,
            "conditions": {
                "temperature": self.conditions.temperature,
                "humidity": self.conditions.humidity,
                "noise_level": self.conditions.noise_level,
                "rush_multiplier": self.conditions.rush_multiplier,
                "time_pressure": self.conditions.time_pressure,
                "crisis_active": self.conditions.crisis_active,
                "crisis_type": self.conditions.crisis_type
            },
            "stations": {
                location.value: {
                    "name": station.name,
                    "current_agents": list(station.current_agents),
                    "available_capacity": station.available_capacity,
                    "cleanliness": station.cleanliness,
                    "equipment_status": [
                        {
                            "name": eq.name,
                            "available": eq.is_available,
                            "condition": eq.condition,
                            "in_use": eq.in_use_by is not None
                        }
                        for eq in station.equipment
                    ]
                }
                for location, station in self.stations.items()
            },
            "inventory": self.global_inventory.copy(),
            "metrics": self.metrics.copy()
        }