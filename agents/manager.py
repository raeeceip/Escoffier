"""
Agent Manager - Coordinates multi-agent kitchen simulation
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import uuid

from config import Config
from database.models import Agent, Skill, Task, AgentAction, Communication
from database import DatabaseManager
from providers.llm import LLMProvider, get_llm_provider
from kitchen.engine import KitchenEngine
from escoffier_types import AgentType, AgentStatus, TaskType, ActionType, TaskStatus

logger = logging.getLogger(__name__)


class CoordinationMode(Enum):
    """Agent coordination modes"""
    HIERARCHICAL = "hierarchical"
    PEER_TO_PEER = "peer_to_peer"
    DEMOCRATIC = "democratic"
    ADAPTIVE = "adaptive"


@dataclass
class AgentContext:
    """Context information for an agent"""
    agent_id: str
    name: str
    agent_type: AgentType
    skills: List[str]
    llm_provider: str = "openai"  # LLM provider for this agent
    model_name: str = "gpt-3.5-turbo"  # Model name for this agent
    current_station: Optional[str] = None
    current_task: Optional[str] = None
    status: AgentStatus = AgentStatus.IDLE
    performance_score: float = 1.0
    stress_level: float = 0.0
    energy_level: float = 1.0
    memory: Dict[str, Any] = field(default_factory=dict)
    communication_history: List[Dict] = field(default_factory=list)
    
    def update_performance(self, task_success: bool, completion_time: float):
        """Update agent performance based on task completion"""
        base_score = 1.0 if task_success else 0.5
        time_factor = max(0.1, 1.0 - (completion_time / 300))  # 5-minute baseline
        self.performance_score = 0.8 * self.performance_score + 0.2 * (base_score * time_factor)
        
    def update_stress(self, stress_delta: float):
        """Update agent stress level"""
        self.stress_level = max(0.0, min(1.0, self.stress_level + stress_delta))
        
    def update_energy(self, energy_delta: float):
        """Update agent energy level"""
        self.energy_level = max(0.0, min(1.0, self.energy_level + energy_delta))


class AgentManager:
    """Manages multiple agents in kitchen simulation"""
    
    def __init__(self, config: Config, db_manager: DatabaseManager, kitchen_engine: KitchenEngine):
        self.config = config
        self.db_manager = db_manager
        self.kitchen_engine = kitchen_engine
        self.agents: Dict[str, AgentContext] = {}
        self.llm_providers: Dict[str, LLMProvider] = {}
        self.coordination_mode = CoordinationMode.HIERARCHICAL
        self.communication_log: List[Dict] = []
        self.task_queue: List[str] = []
        self.active_collaborations: Dict[str, Set[str]] = {}
        
        # Performance tracking
        self.collaboration_metrics = {
            'successful_collaborations': 0,
            'failed_collaborations': 0,
            'communication_efficiency': 0.0,
            'task_completion_rate': 0.0
        }
        
    async def initialize(self):
        """Initialize agent manager with LLM providers"""
        # Initialize LLM providers
        try:
            llm_manager = get_llm_provider()  # Get the provider manager
            self.llm_providers: Dict[str, LLMProvider] = llm_manager.providers.copy()
            logger.info(f"Initialized LLM providers: {list(self.llm_providers.keys())}")
        except Exception as e:
            logger.warning(f"Failed to initialize LLM providers: {e}")
            self.llm_providers = {}
        
        # Load agents from database
        await self.load_agents()
        
    async def load_agents(self):
        """Load agents from database"""
        with self.db_manager.get_session() as session:
            db_agents = session.query(Agent).all()
            
            for db_agent in db_agents:
                # Map role to agent type for compatibility
                role_to_type_map = {
                    'executive_chef': AgentType.HEAD_CHEF,
                    'sous_chef': AgentType.SOUS_CHEF,
                    'chef_de_partie': AgentType.SOUS_CHEF,
                    'line_cook': AgentType.LINE_COOK,
                    'prep_cook': AgentType.PREP_COOK,
                    'kitchen_porter': AgentType.PREP_COOK
                }
                
                agent_type = role_to_type_map.get(db_agent.role.value, AgentType.LINE_COOK)
                
                agent_context = AgentContext(
                    agent_id=db_agent.id,
                    name=db_agent.name,
                    agent_type=agent_type,
                    skills=[skill.name for skill in db_agent.skills],
                    llm_provider=db_agent.model_provider,
                    model_name=db_agent.model_name,
                    status=AgentStatus.IDLE  # Default status
                )
                self.agents[db_agent.id] = agent_context
                logger.info(f"Loaded agent {db_agent.name} ({db_agent.role.value}) -> {agent_type.value}")
        
        logger.info(f"Loaded {len(self.agents)} agents from database")
                
    async def create_agent(
        self,
        name: str,
        agent_type: AgentType,
        skills: List[str],
        llm_provider: str = 'openai'
    ) -> str:
        """Create a new agent"""
        
        logger.info(f"Creating agent with provider: {llm_provider}")
        
        # Map AgentType to KitchenRole
        from database.models import KitchenRole
        role_mapping = {
            AgentType.HEAD_CHEF: KitchenRole.EXECUTIVE_CHEF,
            AgentType.SOUS_CHEF: KitchenRole.SOUS_CHEF,
            AgentType.LINE_COOK: KitchenRole.LINE_COOK,
            AgentType.PREP_COOK: KitchenRole.PREP_COOK,
        }
        kitchen_role = role_mapping.get(agent_type, KitchenRole.LINE_COOK)
        
        # Map providers to their default models
        provider_models = {
            'openai': 'gpt-3.5-turbo',
            'anthropic': 'claude-3-haiku-20240307',
            'cohere': 'command-r',
            'huggingface': 'microsoft/DialoGPT-medium'
        }
        model_name = provider_models.get(llm_provider, 'gpt-3.5-turbo')
        
        # Create in database
        with self.db_manager.get_session() as session:
            db_agent = Agent(
                name=name,
                role=kitchen_role,  # Use the mapped kitchen role
                model_provider=llm_provider,
                model_name=model_name,  # Use provider-specific model
                experience_level=0
            )
            session.add(db_agent)
            session.commit()  # Commit to get the auto-generated ID
            
            agent_id = str(db_agent.id)  # Get the auto-generated ID
            
            # Add skills through the relationship
            for skill_name in skills:
                # First check if skill exists
                existing_skill = session.query(Skill).filter(Skill.name == skill_name).first()
                if existing_skill:
                    # Use existing skill
                    db_agent.skills.append(existing_skill)
                else:
                    # Create new skill and associate it
                    new_skill = Skill(
                        name=skill_name,
                        description=f"Skill: {skill_name}",
                        category="cooking",
                        difficulty=5
                    )
                    session.add(new_skill)
                    db_agent.skills.append(new_skill)
                
            session.commit()
            
        # Create context
        agent_context = AgentContext(
            agent_id=agent_id,
            name=name,
            agent_type=agent_type,
            skills=skills,
            llm_provider=llm_provider,
            model_name=model_name
        )
        self.agents[agent_id] = agent_context
        
        logger.info(f"Created agent {name} ({agent_type.value}) with ID {agent_id}")
        return agent_id
        
    def _get_agent_prompt_template(self, agent_type: AgentType) -> str:
        """Get prompt template for agent type"""
        templates = {
            AgentType.HEAD_CHEF: """You are the Head Chef managing a busy kitchen. You coordinate tasks, make strategic decisions, and ensure quality standards. Your responsibilities include:
- Delegating tasks to other chefs
- Managing kitchen workflow and timing
- Making final decisions on dish preparation
- Handling crisis situations
- Maintaining quality standards

Current kitchen state: {kitchen_state}
Current task: {current_task}
Team status: {team_status}

Provide your decision or action:""",

            AgentType.SOUS_CHEF: """You are a Sous Chef assisting the Head Chef and managing specific kitchen stations. Your responsibilities include:
- Managing assigned stations efficiently
- Training junior staff
- Ensuring food quality and safety
- Coordinating with other stations
- Stepping in during emergencies

Current station: {current_station}
Current task: {current_task}
Kitchen status: {kitchen_status}

Provide your action:""",

            AgentType.LINE_COOK: """You are a Line Cook focused on executing specific cooking tasks efficiently. Your responsibilities include:
- Preparing ingredients and dishes according to recipes
- Maintaining your station
- Following chef instructions precisely
- Communicating status updates
- Working as part of the team

Current station: {current_station}
Current task: {current_task}
Available ingredients: {ingredients}

Provide your cooking action:""",

            AgentType.PREP_COOK: """You are a Prep Cook responsible for ingredient preparation and kitchen setup. Your responsibilities include:
- Preparing ingredients for service
- Maintaining ingredient inventory
- Setting up stations
- Basic food preparation tasks
- Supporting other kitchen staff

Current prep tasks: {prep_tasks}
Inventory status: {inventory}
Station assignments: {stations}

Provide your prep action:"""
        }
        
        return templates.get(agent_type, "You are a kitchen assistant. Help with cooking tasks as needed.")
        
    async def assign_task(self, agent_id: str, task_data: Dict) -> str:
        """Assign a task to an agent"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
            
        agent = self.agents[agent_id]
        
        # Create task in database
        with self.db_manager.get_session() as session:
            from database.models import TaskStatus as DBTaskStatus
            task = Task(
                agent_id=int(agent_id),  # Convert to int since agent_id is stored as int in DB
                task_type=task_data['type'],
                description=task_data['description'],
                parameters=task_data.get('parameters', {}),
                status=DBTaskStatus.PENDING.value,  # Use database TaskStatus enum value
                priority=task_data.get('priority', 1),
                estimated_duration=task_data.get('duration_minutes', 10)
            )
            session.add(task)
            session.commit()
            session.refresh(task)  # Get the auto-generated ID
            
            task_id = str(task.id)  # Convert back to string for return
            
        # Update agent context
        agent.current_task = task_id
        agent.status = AgentStatus.BUSY
        
        logger.info(f"Assigned task {task_id} to agent {agent.name}")
        return task_id
        
    async def execute_agent_action(self, agent_id: str, context: Dict) -> Dict:
        """Execute an action using the agent's LLM"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
            
        agent = self.agents[agent_id]
        
        # Get LLM provider
        with self.db_manager.get_session() as session:
            db_agent = session.query(Agent).filter(Agent.id == agent_id).first()
            if not db_agent:
                raise ValueError(f"Agent {agent_id} not found in database")
                
            provider_name = db_agent.model_provider  # Correct field name
            if provider_name not in self.llm_providers:
                raise ValueError(f"LLM provider {provider_name} not available")
                
            provider = self.llm_providers[provider_name]
            
            # Prepare prompt
            # Get agent type from role for prompt template
            role_to_type_map = {
                'executive_chef': AgentType.HEAD_CHEF,
                'sous_chef': AgentType.SOUS_CHEF,
                'line_cook': AgentType.LINE_COOK,
                'prep_cook': AgentType.PREP_COOK,
                'kitchen_porter': AgentType.PREP_COOK
            }
            agent_type = role_to_type_map.get(db_agent.role.value, AgentType.LINE_COOK)
            prompt_template = self._get_agent_prompt_template(agent_type)
            
            prompt = prompt_template.format(
                kitchen_state=context.get('kitchen_state', ''),
                current_task=context.get('current_task', ''),
                team_status=context.get('team_status', ''),
                current_station=db_agent.assigned_station or '',
                kitchen_status=context.get('kitchen_status', ''),
                ingredients=context.get('ingredients', ''),
                prep_tasks=context.get('prep_tasks', ''),
                inventory=context.get('inventory', ''),
                stations=context.get('stations', '')
            )
            
            # Get LLM response
            try:
                response = await provider.generate_response(
                    prompt=prompt,
                    max_tokens=200,
                    temperature=0.7
                )
                
                # Parse action from response
                action_data = self._parse_agent_response(response, agent.agent_type)
                
                # Record action in database
                action_id = str(uuid.uuid4())
                action = AgentAction(
                    agent_id=agent_id,
                    task_id=agent.current_task,
                    action_type=action_data['type'],
                    description=action_data['description'],
                    context=action_data.get('parameters', {}),
                    llm_prompt=prompt,
                    llm_response=response,
                    created_at=datetime.utcnow()
                )
                session.add(action)
                session.commit()
                
                # Update agent memory
                agent.memory[f"action_{action_id}"] = {
                    'type': action_data['type'],
                    'description': action_data['description'],
                    'timestamp': datetime.utcnow().isoformat(),
                    'context': context
                }
                
                logger.info(f"Agent {agent.name} executed action: {action_data['description']}")
                return action_data
                
            except Exception as e:
                logger.error(f"Failed to execute agent action for {agent.name}: {e}")
                raise
                
    def _parse_agent_response(self, response: str, agent_type: AgentType) -> Dict:
        """Parse LLM response into structured action"""
        # Simple parsing - could be enhanced with more sophisticated NLP
        response_lower = response.lower().strip()
        
        # Default action structure
        action = {
            'type': ActionType.COMMUNICATE.value,
            'description': response,
            'parameters': {}
        }
        
        # Parse based on keywords and agent type
        if 'cook' in response_lower or 'prepare' in response_lower:
            action['type'] = ActionType.COOK.value
        elif 'move' in response_lower or 'go to' in response_lower:
            action['type'] = ActionType.MOVE.value
        elif 'get' in response_lower or 'fetch' in response_lower:
            action['type'] = ActionType.GET_INGREDIENT.value
        elif 'clean' in response_lower:
            action['type'] = ActionType.CLEAN.value
        elif 'help' in response_lower or 'assist' in response_lower:
            action['type'] = ActionType.COLLABORATE.value
        elif 'delegate' in response_lower and agent_type in [AgentType.HEAD_CHEF, AgentType.SOUS_CHEF]:
            action['type'] = ActionType.DELEGATE.value
            
        return action
        
    async def facilitate_communication(self, from_agent_id: str, to_agent_id: str, message: str) -> bool:
        """Facilitate communication between agents"""
        if from_agent_id not in self.agents or to_agent_id not in self.agents:
            return False
            
        from_agent = self.agents[from_agent_id]
        to_agent = self.agents[to_agent_id]
        
        # Record communication
        comm_id = str(uuid.uuid4())
        with self.db_manager.get_session() as session:
            communication = Communication(
                id=comm_id,
                from_agent_id=from_agent_id,
                to_agent_id=to_agent_id,
                message=message,
                communication_type='direct',
                sent_at=datetime.utcnow()
            )
            session.add(communication)
            session.commit()
            
        # Update agent contexts
        comm_data = {
            'id': comm_id,
            'from': from_agent.name,
            'to': to_agent.name,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        from_agent.communication_history.append(comm_data)
        to_agent.communication_history.append(comm_data)
        self.communication_log.append(comm_data)
        
        logger.info(f"Communication from {from_agent.name} to {to_agent.name}: {message}")
        return True
        
    async def coordinate_collaboration(self, task_id: str, agent_ids: List[str]) -> str:
        """Coordinate collaboration between multiple agents"""
        collaboration_id = str(uuid.uuid4())
        
        # Create collaboration group
        self.active_collaborations[collaboration_id] = set(agent_ids)
        
        # Update agent statuses
        for agent_id in agent_ids:
            if agent_id in self.agents:
                self.agents[agent_id].status = AgentStatus.COLLABORATING
                
        # Facilitate initial coordination
        if len(agent_ids) > 1:
            lead_agent_id = agent_ids[0]  # First agent leads
            for other_agent_id in agent_ids[1:]:
                await self.facilitate_communication(
                    lead_agent_id,
                    other_agent_id,
                    f"Let's collaborate on task {task_id}. I'll coordinate our efforts."
                )
                
        logger.info(f"Started collaboration {collaboration_id} with agents: {agent_ids}")
        return collaboration_id
        
    async def handle_crisis(self, crisis_type: str, context: Dict) -> List[Dict]:
        """Handle crisis situations with agent coordination"""
        logger.warning(f"Handling crisis: {crisis_type}")
        
        # Get all available agents
        available_agents = [
            agent for agent in self.agents.values()
            if agent.status in [AgentStatus.IDLE, AgentStatus.BUSY]
        ]
        
        crisis_responses = []
        
        if crisis_type == 'equipment_failure':
            # Prioritize head chef and sous chefs for decision making
            decision_makers = [
                agent for agent in available_agents
                if agent.agent_type in [AgentType.HEAD_CHEF, AgentType.SOUS_CHEF]
            ]
            
            for agent in decision_makers[:2]:  # Top 2 decision makers
                response = await self.execute_agent_action(
                    agent.agent_id,
                    {
                        'current_task': f"Handle equipment failure: {context.get('equipment', 'unknown')}",
                        'kitchen_state': context.get('kitchen_state', ''),
                        'crisis_context': context
                    }
                )
                crisis_responses.append({
                    'agent_id': agent.agent_id,
                    'agent_name': agent.name,
                    'response': response
                })
                
        elif crisis_type == 'time_pressure':
            # All agents contribute to speed up
            for agent in available_agents:
                response = await self.execute_agent_action(
                    agent.agent_id,
                    {
                        'current_task': f"Speed up due to time pressure",
                        'kitchen_state': context.get('kitchen_state', ''),
                        'time_remaining': context.get('time_remaining', 0)
                    }
                )
                crisis_responses.append({
                    'agent_id': agent.agent_id,
                    'agent_name': agent.name,
                    'response': response
                })
                
        # Update stress levels
        for agent in available_agents:
            agent.update_stress(0.2)  # Crisis increases stress
            
        return crisis_responses
        
    def get_team_status(self) -> Dict:
        """Get current status of all agents"""
        status = {
            'total_agents': len(self.agents),
            'agents_by_status': {},
            'agents_by_type': {},
            'average_performance': 0.0,
            'average_stress': 0.0,
            'average_energy': 0.0,
            'active_collaborations': len(self.active_collaborations),
            'recent_communications': len([
                comm for comm in self.communication_log
                if (datetime.utcnow() - datetime.fromisoformat(comm['timestamp'].replace('Z', '+00:00'))).seconds < 300
            ])
        }
        
        if not self.agents:
            return status
            
        # Count by status and type
        for agent in self.agents.values():
            status['agents_by_status'][agent.status.value] = status['agents_by_status'].get(agent.status.value, 0) + 1
            status['agents_by_type'][agent.agent_type.value] = status['agents_by_type'].get(agent.agent_type.value, 0) + 1
            
        # Calculate averages
        status['average_performance'] = sum(agent.performance_score for agent in self.agents.values()) / len(self.agents)
        status['average_stress'] = sum(agent.stress_level for agent in self.agents.values()) / len(self.agents)
        status['average_energy'] = sum(agent.energy_level for agent in self.agents.values()) / len(self.agents)
        
        return status
        
    async def update_agent_skills(self, agent_id: str, task_success: bool, skill_name: str):
        """Update agent skills based on task performance"""
        if agent_id not in self.agents:
            return
            
        with self.db_manager.get_session() as session:
            skill = session.query(Skill).filter(
                Skill.agent_id == agent_id,
                Skill.name == skill_name
            ).first()
            
            if skill:
                # Update proficiency based on success
                delta = 0.1 if task_success else -0.05
                skill.proficiency = max(0.0, min(1.0, skill.proficiency + delta))
                session.commit()
                
                logger.info(f"Updated skill {skill_name} for agent {agent_id}: proficiency = {skill.proficiency:.2f}")
                
    async def cleanup(self):
        """Cleanup resources"""
        # Reset agent statuses
        for agent in self.agents.values():
            agent.status = AgentStatus.IDLE
            agent.current_task = None
            
        # Clear active collaborations
        self.active_collaborations.clear()
        
        logger.info("Agent manager cleaned up")