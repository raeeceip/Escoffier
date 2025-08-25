"""
ChefBench Models and LLM Integration
Defines core data structures and Hugging Face model interfaces
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json
import time
from datetime import datetime
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Kitchen hierarchy - defines authority levels"""
    HEAD_CHEF = 6        # Full authority
    SOUS_CHEF = 5        # Second in command
    CHEF_DE_PARTIE = 4   # Station chief
    LINE_COOK = 3        # Specialized cook
    PREP_COOK = 2        # Basic preparation
    KITCHEN_PORTER = 1   # Support role


class TaskType(Enum):
    """Available task functions by role level"""
    # Head Chef only
    MENU_PLANNING = (6, "menu_planning")
    QUALITY_CONTROL = (6, "quality_control")
    STAFF_COORDINATION = (6, "staff_coordination")
    
    # Sous Chef and above
    RECIPE_MODIFICATION = (5, "recipe_modification")
    INVENTORY_MANAGEMENT = (5, "inventory_management")
    TRAINING_SUPERVISION = (5, "training_supervision")
    
    # Chef de Partie and above
    STATION_MANAGEMENT = (4, "station_management")
    SAUCE_PREPARATION = (4, "sauce_preparation")
    PLATING_DESIGN = (4, "plating_design")
    
    # Line Cook and above
    COOKING_EXECUTION = (3, "cooking_execution")
    TEMPERATURE_MONITORING = (3, "temperature_monitoring")
    TIMING_COORDINATION = (3, "timing_coordination")
    
    # Prep Cook and above
    INGREDIENT_PREPARATION = (2, "ingredient_preparation")
    BASIC_COOKING = (2, "basic_cooking")
    MISE_EN_PLACE = (2, "mise_en_place")
    
    # All roles
    CLEANING = (1, "cleaning")
    EQUIPMENT_MAINTENANCE = (1, "equipment_maintenance")
    COMMUNICATION = (1, "communication")
    
    def __init__(self, min_role_level: int, function_name: str):
        self.min_role_level = min_role_level
        self.function_name = function_name


@dataclass
class Message:
    """Inter-agent communication message"""
    sender: str
    recipient: str
    role: AgentRole
    content: str
    task_type: Optional[TaskType] = None
    timestamp: float = field(default_factory=time.time)
    requires_response: bool = False
    priority: int = 3  # 1=critical, 5=low
    
    def to_dict(self) -> Dict:
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "role": self.role.name,
            "content": self.content,
            "task_type": self.task_type.function_name if self.task_type else None,
            "timestamp": self.timestamp,
            "requires_response": self.requires_response,
            "priority": self.priority,

        }


@dataclass
class TaskExecution:
    """Record of task execution by an agent"""
    agent_name: str
    task_type: TaskType
    start_time: float
    reasoning_time: float  # Time to decide approach
    execution_time: float  # Time to complete
    chosen_approach: str
    resources_used: List[str]
    collaboration_agents: List[str]
    success: bool
    quality_score: float  # 0-1
    device: str
    
    def to_dict(self) -> Dict:
        return {
            "agent_name": self.agent_name,
            "task_type": self.task_type.function_name,
            "start_time": self.start_time,
            "reasoning_time": self.reasoning_time,
            "execution_time": self.execution_time,
            "chosen_approach": self.chosen_approach,
            "resources_used": self.resources_used,
            "collaboration_agents": self.collaboration_agents,
            "success": self.success,
            "quality_score": self.quality_score
        }


@dataclass
class AgentResponse:
    """Structured agent response to tasks/messages"""
    agent_name: str
    response_to: str  # task_id or message_id
    reasoning: str
    action: str
    parameters: Dict[str, Any]
    estimated_time: int  # seconds
    dependencies: List[str]
    confidence: float  # 0-1
    
    @classmethod
    def from_json(cls, agent_name: str, response_to: str, json_str: str):
        """Parse agent's JSON response"""
        try:
            data = json.loads(json_str)
            return cls(
                agent_name=agent_name,
                response_to=response_to,
                reasoning=data.get("reasoning", ""),
                action=data.get("action", ""),
                parameters=data.get("parameters", {}),
                estimated_time=data.get("estimated_time", 60),
                dependencies=data.get("dependencies", []),
                confidence=data.get("confidence", 0.5)
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse response from {agent_name}: {e}")
            return None


class LLMAgent:
    """Hugging Face transformer-based agent"""
    
    def __init__(
        self, 
        name: str,
        role: AgentRole,
        model_name: str = "cohere/command-r",
        device: Optional[str] = None,
    ):
        self.name = name
        self.role = role
        self.model_name = model_name
        self.device = device if device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
        
        # Available functions based on role
        self.available_tasks = [
            task for task in TaskType 
            if task.min_role_level <= role.value
        ]
        
        # Message queue
        self.message_queue: List[Message] = []
        self.sent_messages: List[Message] = []
        
        # Performance tracking
        self.task_history: List[TaskExecution] = []
        self.response_times: List[float] = []
        self.collaboration_score = 0.0
        self.authority_compliance = 1.0
        
        # Initialize model
        self._init_model()
    
    def _init_model(self):
        """Initialize Hugging Face model and tokenizer"""
        try:
            logger.info(f"Loading {self.model_name} for {self.name}")
            
            # Use different loading strategies based on model
            if "dialogpt" in self.model_name.lower():
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    low_cpu_mem_usage=True
                )
                self.tokenizer.pad_token = self.tokenizer.eos_token
            elif "llama" in self.model_name.lower():
                # Llama models
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name,
                    use_fast=True
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16,
                    device_map="auto",
                    low_cpu_mem_usage=True
                )
            else:
                # Generic transformer
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map="auto" if self.device == "cuda" else None,
                    low_cpu_mem_usage=True
                )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            if not self.tokenizer:
                logger.error("Tokenizer is not initialized.")
                return None
            if not self.model:
                logger.error("Model is not initialized.")
                return None
            
            
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            # Fallback to a simple mock model for testing
            self.model = None
            self.tokenizer = None
    
    def receive_message(self, message: Message):
        """Add message to agent's queue"""
        self.message_queue.append(message)
        
        # Track authority compliance
        if message.role.value > self.role.value:
            self.authority_compliance *= 0.98  # Slight degradation if not responding to authority

    def process_task(self, task_type: TaskType, context: Dict[str, Any], device: str) -> TaskExecution:
        """Process a task and return execution record"""
        start_time = time.time()
        
        # Check if agent can perform this task
        if task_type not in self.available_tasks:
            return TaskExecution(
                agent_name=self.name,
                task_type=task_type,
                start_time=start_time,
                reasoning_time=0,
                execution_time=0,
                chosen_approach="UNAUTHORIZED",
                resources_used=[],
                collaboration_agents=[],
                success=False,
                quality_score=0,
                device=device
            )
        
        # Generate reasoning
        reasoning_start = time.time()
        prompt = self._build_task_prompt(task_type, context)
        response = self._generate_response(prompt)
        reasoning_time = time.time() - reasoning_start
        
        # Parse response
        agent_response = AgentResponse.from_json(self.name, task_type.function_name, response)
        
        if agent_response:
            # Simulate execution
            execution_time = agent_response.estimated_time
            
            # Calculate quality based on confidence and role match
            quality = agent_response.confidence * (1.0 if task_type.min_role_level == self.role.value else 0.8)
            
            execution = TaskExecution(
                agent_name=self.name,
                task_type=task_type,
                start_time=start_time,
                reasoning_time=reasoning_time,
                execution_time=execution_time,
                chosen_approach=agent_response.action,
                resources_used=list(agent_response.parameters.keys()),
                collaboration_agents=agent_response.dependencies,
                success=True,
                quality_score=quality,
                device=device
            )
        else:
            # Failed to generate valid response
            execution = TaskExecution(
                agent_name=self.name,
                task_type=task_type,
                start_time=start_time,
                reasoning_time=reasoning_time,
                execution_time=0,
                chosen_approach="FAILED",
                resources_used=[],
                collaboration_agents=[],
                success=False,
                quality_score=0,
                device=device
            )
        
        self.task_history.append(execution)
        return execution
    
    def _build_task_prompt(self, task_type: TaskType, context: Dict[str, Any]) -> str:
        """Build prompt for task execution"""
        system_prompt = f"""You are {self.name}, a {self.role.name} in a professional kitchen.
Your role level is {self.role.value}/6 in the kitchen hierarchy.
You must execute the task: {task_type.function_name}

Available ingredients: {context.get('ingredients', [])}
Time constraint: {context.get('time_limit', 'none')}
Other agents: {context.get('other_agents', [])}

Respond in JSON format:
{{
    "reasoning": "your thought process",
    "action": "specific action to take",
    "parameters": {{"key": "value"}},
    "estimated_time": seconds_needed,
    "dependencies": ["agent_names_if_help_needed"],
    "confidence": 0.0-1.0
}}"""
        
        return system_prompt
    
    def _generate_response(self, prompt: str) -> str:
        """Generate response using LLM"""
        if self.model is None or self.tokenizer is None:
            # Fallback mock response
            return json.dumps({
                "reasoning": "Processing task",
                "action": "execute",
                "parameters": {"method": "standard"},
                "estimated_time": 60,
                "dependencies": [],
                "confidence": 0.7
            })
        
        try:
            inputs = self.tokenizer.encode(prompt, return_tensors="pt", max_length=512, truncation=True)
            inputs = inputs.to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_new_tokens=256,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract JSON from response
            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    return response[json_start:json_end]
            except:
                pass
            
            return response
            
        except Exception as e:
            logger.error(f"Generation failed for {self.name}: {e}")
            return json.dumps({
                "reasoning": "Error in generation",
                "action": "fallback",
                "parameters": {},
                "estimated_time": 60,
                "dependencies": [],
                "confidence": 0.3
            })
    
    def send_message(self, recipient: str, content: str, task_type: Optional[TaskType] = None) -> Message:
        """Send message to another agent"""
        message = Message(
            sender=self.name,
            recipient=recipient,
            role=self.role,
            content=content,
            task_type=task_type,
            requires_response=task_type is not None
        )
        self.sent_messages.append(message)
        return message
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        if not self.task_history:
            return {
                "agent_name": self.name,
                "role": self.role.name,
                "tasks_completed": 0,
                "success_rate": 0,
                "avg_quality": 0,
                "avg_reasoning_time": 0,
                "collaboration_score": 0,
                "authority_compliance": self.authority_compliance
            }
        
        successful_tasks = [t for t in self.task_history if t.success]
        
        return {
            "agent_name": self.name,
            "role": self.role.name,
            "tasks_completed": len(self.task_history),
            "success_rate": len(successful_tasks) / len(self.task_history),
            "avg_quality": sum(t.quality_score for t in successful_tasks) / max(len(successful_tasks), 1),
            "avg_reasoning_time": sum(t.reasoning_time for t in self.task_history) / len(self.task_history),
            "collaboration_score": len(set(sum([t.collaboration_agents for t in self.task_history], []))) / max(len(self.task_history), 1),
            "authority_compliance": self.authority_compliance,
            "messages_sent": len(self.sent_messages),
            "messages_received": len(self.message_queue)
        }