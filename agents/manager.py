"""
Agent Manager - Coordinates multi-agent kitchen simulation with AutoGen
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import uuid
import json

# AutoGen imports
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.models.anthropic import AnthropicChatCompletionClient

from config import Config
from database.models import Agent, Skill, Task, AgentAction, Communication
from database import DatabaseManager
from providers.llm import LLMProvider, get_llm_provider
from kitchen.engine import KitchenEngine
from escoffier_types import AgentType, AgentStatus, ActionType, TaskStatus

logger = logging.getLogger(__name__)


class CoordinationMode(Enum):
    """Agent coordination modes"""
    HIERARCHICAL = "hierarchical"
    PEER_TO_PEER = "peer_to_peer"
    DEMOCRATIC = "democratic"
    ADAPTIVE = "adaptive"


@dataclass
class AgentContext:
    """Context information for an agent with AutoGen"""
    agent_id: str
    name: str
    agent_type: AgentType
    skills: List[str]
    llm_provider: str = "openai"
    model_name: str = "gpt-3.5-turbo"
    current_station: Optional[str] = None
    current_task: Optional[str] = None
    status: AgentStatus = AgentStatus.IDLE
    performance_score: float = 1.0
    stress_level: float = 0.0
    energy_level: float = 1.0
    memory: Dict[str, Any] = field(default_factory=dict)
    communication_history: List[Dict] = field(default_factory=list)
    autogen_agent: Optional[AssistantAgent] = None
    model_client: Optional[Any] = None
    authority_level: int = 1
    
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
    """Manages multiple agents in kitchen simulation using AutoGen"""
    
    def __init__(self, config: Config, db_manager: DatabaseManager, kitchen_engine: KitchenEngine):
        self.config = config
        self.db_manager = db_manager
        self.kitchen_engine = kitchen_engine
        self.agents: Dict[str, AgentContext] = {}
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
        """Initialize AutoGen-based agent manager"""
        logger.info("🤖 Initializing AutoGen-based multi-agent system...")
        
        # Set environment variables early for all providers
        self._set_environment_variables()
        
        # Load agents from database and create AutoGen agents
        await self.load_agents()
        
        logger.info(f"✅ Initialized {len(self.agents)} AutoGen agents")

    def _set_environment_variables(self):
        """Set API key environment variables for all providers"""
        import os
        
        # Set all available API keys in environment
        if self.config.openai.api_key:
            os.environ["OPENAI_API_KEY"] = self.config.openai.api_key
            
        if self.config.anthropic.api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.config.anthropic.api_key
            
        if self.config.cohere.api_key:
            os.environ["COHERE_API_KEY"] = self.config.cohere.api_key
            
        # For Hugging Face, check if HF_TOKEN is already set in environment
        if "HF_TOKEN" not in os.environ:
            logger.warning("HF_TOKEN not found in environment for Hugging Face models")
        
    async def load_agents(self):
        """Load agents from database and create AutoGen agents"""
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
                
                # Create AutoGen agent
                autogen_agent, model_client = await self._create_autogen_agent(agent_type, str(db_agent.name), str(db_agent.model_provider), str(db_agent.model_name))
                logger.info(f"🤖 Created AutoGen agent for {db_agent.name}: {autogen_agent is not None}")
                
                agent_context = AgentContext(
                    agent_id=str(db_agent.id),
                    name=str(db_agent.name),
                    agent_type=agent_type,
                    skills=[skill.name for skill in db_agent.skills],
                    llm_provider=str(db_agent.model_provider),
                    model_name=str(db_agent.model_name),
                    status=AgentStatus.IDLE,
                    autogen_agent=autogen_agent,
                    model_client=model_client,
                    authority_level=self._get_authority_level(agent_type)
                )
                self.agents[str(db_agent.id)] = agent_context
                logger.info(f"✅ Loaded AutoGen agent {db_agent.name} ({db_agent.role.value}) -> {agent_type.value}")
        
        logger.info(f"Loaded {len(self.agents)} AutoGen agents from database")
    
    async def _create_autogen_agent(self, agent_type: AgentType, name: str, provider: str, model_name: str) -> Tuple[Optional[AssistantAgent], Optional[Any]]:
        """Create an AutoGen agent with proper model client"""
        try:
            # Create model client based on provider
            model_client = None
            if provider == "openai":
                model_client = OpenAIChatCompletionClient(model=model_name)
            elif provider == "anthropic":
                model_client = AnthropicChatCompletionClient(model=model_name)
            else:
                logger.warning(f"Unsupported provider {provider} for AutoGen, using OpenAI as fallback")
                model_client = OpenAIChatCompletionClient(model="gpt-3.5-turbo")
            
            # Create system prompt for the agent
            system_prompt = self._create_system_prompt(agent_type, name)
            
            # Sanitize agent name for AutoGen (must be valid Python identifier)
            sanitized_name = self._sanitize_agent_name(name)
            
            # Create AutoGen AssistantAgent
            agent = AssistantAgent(
                name=sanitized_name,
                model_client=model_client,
                system_message=system_prompt
            )
            
            return agent, model_client
            
        except Exception as e:
            logger.error(f"Failed to create AutoGen agent {name}: {e}")
            return None, None
    
    def _sanitize_agent_name(self, name: str) -> str:
        """Sanitize agent name to be a valid Python identifier for AutoGen"""
        import re
        # Replace spaces and special characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Ensure it starts with a letter or underscore
        if sanitized and not (sanitized[0].isalpha() or sanitized[0] == '_'):
            sanitized = f"agent_{sanitized}"
        # Ensure it's not empty
        if not sanitized:
            sanitized = "agent"
        return sanitized
    
    def _create_system_prompt(self, agent_type: AgentType, name: str) -> str:
        """Create system prompt for agent based on type"""
        base_prompt = f"""You are {name}, a {agent_type.value} in a professional kitchen simulation.

Your role: {agent_type.value}
Your responsibilities: {self._get_role_responsibilities(agent_type)}

IMPORTANT RESPONSE FORMAT:
Always respond with valid JSON in this exact format:
{{
    "analysis": "Your detailed analysis of the situation",
    "action": "The specific action you will take",
    "reasoning": "Why you chose this action",
    "communication": "What you would say to other team members",
    "next_steps": "What should happen next"
}}

Guidelines:
- Be professional and realistic for a kitchen environment
- Consider food safety, timing, and quality in all decisions
- Communicate clearly with your team
- Respond naturally as a human chef would
- Focus on practical kitchen tasks and coordination"""
        
        return base_prompt
    
    def _get_role_responsibilities(self, agent_type: AgentType) -> str:
        """Get role-specific responsibilities"""
        responsibilities = {
            AgentType.HEAD_CHEF: "Overall kitchen management, menu planning, quality control, staff coordination",
            AgentType.SOUS_CHEF: "Assistant management, station supervision, recipe development, training",
            AgentType.LINE_COOK: "Order preparation, station maintenance, following recipes, timing coordination",
            AgentType.PREP_COOK: "Ingredient preparation, basic cooking tasks, cleaning, inventory support",
            AgentType.DISHWASHER: "Cleaning, dishwashing, basic prep work, equipment maintenance"
        }
        return responsibilities.get(agent_type, "General kitchen support")
    
    def _get_authority_level(self, agent_type: AgentType) -> int:
        """Get authority level based on agent type"""
        authority_map = {
            AgentType.HEAD_CHEF: 5,
            AgentType.SOUS_CHEF: 4,
            AgentType.LINE_COOK: 2,
            AgentType.PREP_COOK: 1,
            AgentType.DISHWASHER: 1
        }
        return authority_map.get(agent_type, 1)
    
    def get_agent_context(self, agent_id: str) -> Optional[AgentContext]:
        """Get agent context by ID"""
        return self.agents.get(agent_id)
    
    def get_available_agents(self, agent_type: Optional[AgentType] = None) -> List[AgentContext]:
        """Get available agents, optionally filtered by type"""
        available = [agent for agent in self.agents.values() if agent.status == AgentStatus.IDLE]
        if agent_type:
            available = [agent for agent in available if agent.agent_type == agent_type]
        return available
    
    def get_agents_by_skill(self, skill: str) -> List[AgentContext]:
        """Get agents that have a specific skill"""
        return [agent for agent in self.agents.values() if skill in agent.skills]
    
    def update_agent_status(self, agent_id: str, status: AgentStatus):
        """Update agent status"""
        if agent_id in self.agents:
            self.agents[agent_id].status = status
                
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
            'huggingface': 'microsoft/DialoGPT-medium',
            'huggingface_llama': 'meta-llama/Llama-2-7b-chat-hf',
            'huggingface_code': 'codellama/CodeLlama-7b-Instruct-hf',
            'huggingface_mistral': 'mistralai/Mistral-7B-Instruct-v0.1'
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
        
    async def execute_autogen_action(self, agent_id: str, context: Dict) -> Dict:
        """Execute an action using AutoGen agents with JSON-structured responses"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
            
        agent = self.agents[agent_id]
        
        if not agent.autogen_agent:
            raise ValueError(f"No AutoGen agent available for agent {agent.name}")
        
        # Get agent details from database for enhanced context
        with self.db_manager.get_session() as session:
            db_agent = session.query(Agent).filter(Agent.id == agent_id).first()
            if db_agent:
                agent_skills = [skill.name for skill in db_agent.skills]
                try:
                    agent_role = str(db_agent.role.value) if hasattr(db_agent.role, 'value') else "prep_cook"
                except (AttributeError, TypeError):
                    agent_role = "prep_cook"
                
                try:
                    agent_location = str(db_agent.current_location.value) if hasattr(db_agent.current_location, 'value') else "kitchen"
                except (AttributeError, TypeError):
                    agent_location = "kitchen"
                agent_station = db_agent.assigned_station or "unassigned"
                experience_level = getattr(db_agent, 'experience_level', 50)
            else:
                agent_skills = []
                agent_role = "prep_cook"
                agent_location = "kitchen"
                agent_station = "unassigned"
                experience_level = 50
        
        # Enhanced context with agent capabilities and position
        enhanced_context = f"""
CURRENT TASK: {context.get('current_task', 'No specific task')}
KITCHEN STATE: {context.get('kitchen_state', 'Normal operations')}
TEAM STATUS: {context.get('team_status', 'Operating normally')}

YOUR AGENT PROFILE:
- Role: {agent_role}
- Current Location: {agent_location}
- Assigned Station: {agent_station}
- Your Skills: {', '.join(agent_skills) if agent_skills else 'Basic kitchen skills'}
- Experience Level: {experience_level}/100

STATION STATUS:
{self._format_station_status(context.get('kitchen_state', {}))}

Respond with ONLY a valid JSON object for your next action. No additional text or explanations."""
        
        try:
            # Use AutoGen's message-based communication
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Create message for AutoGen agent with proper API call
                    autogen_agent = agent.autogen_agent
                    
                    # Create a user message with the task context
                    user_message = f"""You are working in a kitchen scenario. Here's your current situation:

{enhanced_context}

Please provide your response as a JSON object with these fields:
- action: what you will do (prep, cook, communicate, etc.)
- description: brief description of your action
- reasoning: why you chose this action
- communication: what you would say to teammates (if any)

Example:
{{"action": "prep", "description": "Chopping onions for the pasta", "reasoning": "Need to prepare ingredients before cooking", "communication": "Starting prep work on carbonara ingredients"}}
"""
                    
                    # Generate response using AutoGen model client
                    try:
                        # Use the model client with proper message format
                        model_client = agent.model_client
                        
                        if model_client is None:
                            raise Exception("No model client available")
                        
                        # Import the proper message types for AutoGen
                        from autogen_core.models import SystemMessage, UserMessage
                        
                        # Create proper messages list for the model client
                        messages = [
                            SystemMessage(content="You are a professional kitchen chef assistant."),
                            UserMessage(content=user_message, source="user")
                        ]
                        
                        # Make the API call with proper await
                        response = await model_client.create(messages)
                        
                        # Extract the response text from CreateResult
                        response_text = None
                        if hasattr(response, 'content'):
                            # CreateResult.content should contain the response
                            response_text = response.content
                        elif hasattr(response, 'message') and hasattr(response.message, 'content'):
                            response_text = response.message.content
                        elif hasattr(response, 'text'):
                            response_text = response.text
                        
                        if not response_text:
                            logger.warning(f"Could not extract text from response: {response}")
                            response_text = str(response)
                            
                    except Exception as api_error:
                        logger.warning(f"AutoGen API call failed: {api_error}")
                        # Fallback to a realistic response based on context
                        task_desc = context.get('current_task', 'task')
                        action_type = context.get('task_type', 'general')
                        response_text = f'{{"action": "{action_type}", "description": "Working on {task_desc}", "reasoning": "Following kitchen procedures and applying professional skills", "communication": "Executing {task_desc} with attention to quality and safety"}}'
                    
                    # Ensure response is a string
                    if not isinstance(response_text, str):
                        response_text = str(response_text)
                    
                    # Try to parse JSON response
                    action_data = self._parse_json_response(response_text)
                    
                    if action_data:
                        break
                        
                except Exception as e:
                    logger.warning(f"AutoGen attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        # Create fallback response
                        response_text = f"Agent encountered an error: {e}"
                        action_data = self._create_fallback_action(response_text, agent_role)
                    
            if not action_data:
                # Final fallback
                response_text = "Agent failed to generate valid response"
                action_data = self._create_fallback_action(response_text, agent_role)
            
            # Ensure required fields
            action_data['llm_response'] = response_text
            action_data.setdefault('type', action_data.get('action', 'communicate'))
            action_data.setdefault('description', action_data.get('description', 'Agent performed an action'))
            
            # Record action in database
            with self.db_manager.get_session() as session:
                action_id = str(uuid.uuid4())
                action = AgentAction(
                    agent_id=agent_id,
                    task_id=agent.current_task,
                    action_type=action_data['type'],
                    description=action_data['description'],
                    context=action_data,
                    llm_prompt=enhanced_context,
                    llm_response=response_text,
                    created_at=datetime.utcnow()
                )
                session.add(action)
                session.commit()
                
                # Update agent memory and location if moved
                agent.memory[f"action_{action_id}"] = {
                    'type': action_data['type'],
                    'description': action_data['description'],
                    'timestamp': datetime.utcnow().isoformat(),
                    'context': context
                }
                
                # Update agent location if they moved (skip for now due to type issues)
                # if action_data['type'] == 'move' and action_data.get('location'):
                #     # Database update will be handled elsewhere
                #     pass
                
            logger.info(f"Agent {agent.name} executed action: {action_data['type']} at {action_data.get('location', 'unknown')} - {action_data['description'][:100]}")
            return action_data
            
        except Exception as e:
            logger.error(f"Failed to execute action for {agent.name}: {e}")
            # Return a safe fallback action
            return {
                'type': 'communicate',
                'description': f"I encountered an issue and need to regroup: {str(e)}",
                'action': 'communicate',
                'location': agent_location,
                'communication': f"I need help - encountered an error: {str(e)}",
                'parameters': {'error': str(e)},
                'llm_response': f"Error: {str(e)}"
            }
                
    def _parse_natural_response(self, response: str, agent_type: AgentType) -> Dict:
        """Parse natural language response into structured action"""
        response_lower = response.lower().strip()
        
        # Default action structure
        action = {
            'type': ActionType.COMMUNICATE.value,
            'description': response,
            'parameters': {},
            'communication': self._extract_communication(response),
            'location': self._extract_location(response)
        }
        
        # Parse based on keywords and natural language patterns
        if any(word in response_lower for word in ['cook', 'prepare', 'grill', 'saute', 'bake', 'fry']):
            action['type'] = ActionType.COOK.value
            action['parameters']['cooking_method'] = self._extract_cooking_method(response)
        elif any(word in response_lower for word in ['move', 'go to', 'head to', 'walk to']):
            action['type'] = ActionType.MOVE.value
            action['parameters']['destination'] = self._extract_location(response)
        elif any(word in response_lower for word in ['get', 'fetch', 'grab', 'take', 'ingredient']):
            action['type'] = ActionType.GET_INGREDIENT.value
            action['parameters']['ingredient'] = self._extract_ingredient(response)
        elif any(word in response_lower for word in ['clean', 'sanitize', 'wash', 'wipe']):
            action['type'] = ActionType.CLEAN.value
            action['parameters']['area'] = self._extract_cleaning_area(response)
        elif any(word in response_lower for word in ['help', 'assist', 'work with', 'collaborate']):
            action['type'] = ActionType.COLLABORATE.value
        elif any(word in response_lower for word in ['organize', 'arrange', 'setup', 'prep']):
            action['type'] = ActionType.PREP.value
        elif 'delegate' in response_lower and agent_type in [AgentType.HEAD_CHEF, AgentType.SOUS_CHEF]:
            action['type'] = ActionType.DELEGATE.value
            action['parameters']['task'] = self._extract_delegation_task(response)
            
        return action
    
    def _extract_cooking_method(self, response: str) -> str:
        """Extract cooking method from response"""
        methods = ['grill', 'saute', 'bake', 'fry', 'boil', 'steam', 'roast']
        response_lower = response.lower()
        for method in methods:
            if method in response_lower:
                return method
        return 'prepare'
    
    def _extract_ingredient(self, response: str) -> str:
        """Extract ingredient from response"""
        # Look for common ingredients
        import re
        # Simple extraction - look for words after "get", "fetch", etc.
        match = re.search(r'(?:get|fetch|grab|take)\s+([a-zA-Z\s]+)', response, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return 'ingredients'
    
    def _extract_cleaning_area(self, response: str) -> str:
        """Extract cleaning area from response"""
        areas = ['station', 'grill', 'counter', 'equipment', 'dishes', 'utensils']
        response_lower = response.lower()
        for area in areas:
            if area in response_lower:
                return area
        return 'workspace'
    
    def _extract_delegation_task(self, response: str) -> str:
        """Extract delegation task from response"""
        # Simple extraction of task being delegated
        import re
        match = re.search(r'delegate\s+(.+?)(?:\.|$)', response, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return 'task'
    
    def _extract_communication(self, response: str) -> str:
        """Extract communication content from response"""
        # Look for quoted speech or direct communication
        import re
        quotes = re.findall(r'"([^"]*)"', response)
        if quotes:
            return quotes[0]
        
        # Look for communication indicators
        comm_indicators = ['tell', 'ask', 'say', 'communicate', 'coordinate']
        for indicator in comm_indicators:
            if indicator in response.lower():
                # Extract the sentence containing the communication
                sentences = response.split('.')
                for sentence in sentences:
                    if indicator in sentence.lower():
                        return sentence.strip()
        
        # Return first 150 chars as communication summary
        return response[:150].strip()
    
    def _extract_location(self, response: str) -> str:
        """Extract location/station from response"""
        response_lower = response.lower()
        
        # Station keywords
        stations = {
            'grill': 'grill',
            'saute': 'saute', 
            'prep': 'prep',
            'baking': 'baking',
            'cold': 'cold_prep',
            'expedite': 'expedite',
            'dish': 'dish',
            'pantry': 'pantry',
            'walk-in': 'cold_storage'
        }
        
        for keyword, station in stations.items():
            if keyword in response_lower:
                return station
                
        return 'kitchen'
        
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
                response = await self.execute_autogen_action(
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
                response = await self.execute_autogen_action(
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
        
    def _get_role_prompt(self, agent_type: AgentType, name: str) -> str:
        """Get role-specific system prompt for structured JSON+text responses"""
        base_prompt = f"""You are {name}, a professional kitchen staff member working in a multi-agent kitchen simulation.

CRITICAL: You must respond with ONLY a JSON object. No additional text, explanations, or code blocks.

Your response must be a valid JSON object with this exact structure:
{{
    "action": "action_type",
    "location": "station_name", 
    "description": "detailed natural language description of what you're doing",
    "communication": "any message to team members (or empty string)",
    "reasoning": "brief explanation of why you chose this action",
    "duration_estimate": "estimated time in minutes",
    "tools_needed": ["list", "of", "tools"],
    "ingredients_needed": ["list", "of", "ingredients"],
    "next_steps": ["planned", "follow-up", "actions"]
}}

AVAILABLE ACTIONS: communicate, cook, move, organize, clean, collaborate, delegate
AVAILABLE LOCATIONS: prep, grill, saute, baking, cold_prep, expedite, dish, pantry, walk_in

EXAMPLE RESPONSE:
{{
    "action": "organize",
    "location": "prep",
    "description": "I'll head to the prep station and organize all the ingredients by category. First, I'll group proteins together in the cold storage area, then arrange vegetables by prep priority, and finally set up mise en place for tonight's service.",
    "communication": "Hey team, I'm organizing the prep station. Let me know if you need specific ingredients prepped first!",
    "reasoning": "The prep station needs organization before service begins, and this will help the whole team work more efficiently",
    "duration_estimate": "15",
    "tools_needed": ["containers", "labels", "cutting_boards"],
    "ingredients_needed": ["vegetables", "proteins", "herbs"],
    "next_steps": ["prep vegetables", "check inventory", "coordinate with line cooks"]
}}"""
        
        role_specializations = {
            AgentType.HEAD_CHEF: "Executive Chef - You lead the kitchen, delegate tasks, and make strategic decisions. Focus on oversight and coordination.",
            AgentType.SOUS_CHEF: "Sous Chef - You manage kitchen stations, coordinate teams, and supervise execution. Balance hands-on work with supervision.", 
            AgentType.LINE_COOK: "Line Cook - You execute cooking tasks efficiently and work your assigned station. Focus on cooking and station management.",
            AgentType.PREP_COOK: "Prep Cook - You prepare ingredients, maintain organization, and support the team. Focus on preparation and organization."
        }
        
        role_prompt = f"{base_prompt}\n\nROLE SPECIALIZATION: {role_specializations.get(agent_type, 'Kitchen Staff - You support kitchen operations.')}"
        
        return role_prompt
    
    async def coordinate_agents(self, task_description: str, available_agents: List[AgentContext]) -> List[Dict]:
        """Coordinate multiple agents using AutoGen for task execution"""
        coordination_responses = []
        
        if not available_agents:
            return coordination_responses
        
        # Use the highest authority agent as coordinator
        coordinator = max(available_agents, key=lambda a: a.authority_level)
        
        try:
            # Get coordination response from lead agent
            response = await self.execute_autogen_action(
                coordinator.agent_id,
                {
                    'current_task': f'Coordinate team for: {task_description}',
                    'kitchen_state': 'Team coordination required',
                    'team_status': f'Available agents: {[a.name for a in available_agents]}',
                    'coordination_role': 'lead_coordinator'
                }
            )
            
            coordination_responses.append({
                'agent_id': coordinator.agent_id,
                'agent_name': coordinator.name,
                'role': 'coordinator',
                'response': response
            })
            
            # Get responses from other team members
            for agent in available_agents:
                if agent.agent_id != coordinator.agent_id:
                    response = await self.execute_autogen_action(
                        agent.agent_id,
                        {
                            'current_task': f'Support coordination for: {task_description}',
                            'kitchen_state': f'Following lead of {coordinator.name}',
                            'team_status': f'Working under {coordinator.name}\'s coordination',
                            'coordination_role': 'team_member'
                        }
                    )
                    
                    coordination_responses.append({
                        'agent_id': agent.agent_id,
                        'agent_name': agent.name,
                        'role': 'team_member',
                        'response': response
                    })
                    
        except Exception as e:
            logger.error(f"Coordination failed: {e}")
            # Return basic coordination response
            coordination_responses.append({
                'agent_id': coordinator.agent_id,
                'agent_name': coordinator.name,
                'role': 'coordinator',
                'response': {
                    'action': 'coordinate',
                    'description': f'Basic coordination for {task_description}',
                    'communication': f'Team, let\'s work on {task_description}',
                    'llm_response': f'Coordinating team for {task_description}'
                }
            })
        
        return coordination_responses
    
    def get_orchestration_status(self) -> Dict[str, Any]:
        """Get status of AutoGen-based orchestration system"""
        return {
            "agents_count": len(self.agents),
            "available_agents": [agent.name for agent in self.agents.values() if agent.status == AgentStatus.IDLE],
            "coordination_mode": self.coordination_mode.value,
            "system_ready": len(self.agents) > 0
        }

    def _format_station_status(self, kitchen_state: dict) -> str:
        """Format kitchen station status for display."""
        if not kitchen_state:
            return "Kitchen stations ready for service."
        
        status_lines = []
        for station, status in kitchen_state.items():
            status_lines.append(f"- {station}: {status}")
        
        return "\n".join(status_lines) if status_lines else "Kitchen stations ready for service."
    
    def _parse_json_response(self, response_text: str) -> dict:
        """Parse JSON response from agent, handling various formats."""
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try parsing the entire response as JSON
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            pass
        
        # Return empty dict if no valid JSON found
        return {}
    
    def _create_fallback_action(self, response_text: str, agent_role: str) -> dict:
        """Create a fallback action when JSON parsing fails."""
        return {
            "action": "communicate",
            "reasoning": f"Agent {agent_role} providing update",
            "details": response_text[:200] + "..." if len(response_text) > 200 else response_text,
            "type": "communication"
        }

    async def cleanup(self):
        """Cleanup resources"""
        # Reset agent statuses
        for agent in self.agents.values():
            agent.status = AgentStatus.IDLE
            agent.current_task = None
            
        # Clear active collaborations
        self.active_collaborations.clear()
        
        logger.info("Agent manager cleaned up")