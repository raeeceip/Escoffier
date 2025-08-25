"""
LMM Coordinator for ChefBench
Manages multi-agent message passing and task coordination
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import logging
from models.models import LLMAgent, AgentRole, TaskType, Message, TaskExecution

logger = logging.getLogger(__name__)


class MultiAgentCoordinator:
    """Coordinates multiple LLM agents in kitchen simulation"""
    
    def __init__(self):
        self.agents: Dict[str, LLMAgent] = {}
        self.message_bus: List[Message] = []
        self.task_queue: List[Tuple[str, TaskType, Dict]] = []
        self.execution_history: List[TaskExecution] = []
        self.scenario_start_time: Optional[float] = None
        self.scenario_end_time: Optional[float] = None
        
    def create_agent(
        self, 
        name: str, 
        role: AgentRole,
        model_name: str = "cohere/command-r"
    ) -> LLMAgent:
        """Create and register an agent"""
        if name in self.agents:
            logger.warning(f"Agent {name} already exists, replacing")
        
        agent = LLMAgent(name, role, model_name)
        self.agents[name] = agent
        logger.info(f"Created agent {name} with role {role.name} using {model_name}")
        return agent
    
    def create_agent_team(
        self,
        provider_model: str,
        team_size: int = 4,
        roles: Optional[List[AgentRole]] = None
    ) -> List[LLMAgent]:
        """Create a team of agents using the same model"""
        if roles is None:
            # Default balanced team
            roles = [
                AgentRole.HEAD_CHEF,
                AgentRole.SOUS_CHEF,
                AgentRole.LINE_COOK,
                AgentRole.PREP_COOK
            ][:team_size]
        
        team = []
        for i, role in enumerate(roles):
            name = f"{role.name}_{i+1}"
            agent = self.create_agent(name, role, provider_model)
            team.append(agent)
        
        return team
    
    def create_mixed_provider_team(
        self,
        provider_models: List[Tuple[str, AgentRole]]
    ) -> List[LLMAgent]:
        """Create team with different models for different roles"""
        team = []
        for i, (model, role) in enumerate(provider_models):
            name = f"{role.name}_{model.split('/')[-1][:8]}_{i+1}"
            agent = self.create_agent(name, role, model)
            team.append(agent)
        return team
    
    async def execute_scenario(
        self,
        tasks: List[Tuple[TaskType, Dict[str, Any]]],
        duration_seconds: int = 300
    ) -> Dict[str, Any]:
        """Execute a scenario with given tasks"""
        logger.info(f"Starting scenario with {len(tasks)} tasks, duration: {duration_seconds}s")
        
        self.scenario_start_time = time.time()
        self.scenario_end_time = self.scenario_start_time + duration_seconds
        
        # Assign tasks to agents based on hierarchy
        task_assignments = self._assign_tasks(tasks)
        
        # Process tasks with message passing
        results = await self._process_with_messages(task_assignments, duration_seconds)
        
        # Collect metrics
        metrics = self._collect_scenario_metrics()
        
        return {
            "duration": time.time() - self.scenario_start_time,
            "tasks_completed": len([e for e in self.execution_history if e.success]),
            "total_tasks": len(tasks),
            "agent_metrics": metrics,
            "execution_history": [e.to_dict() for e in self.execution_history],
            "message_count": len(self.message_bus)
        }
    
    def _assign_tasks(
        self, 
        tasks: List[Tuple[TaskType, Dict[str, Any]]]
    ) -> Dict[str, List[Tuple[TaskType, Dict]]]:
        """Assign tasks to agents based on role hierarchy"""
        assignments = defaultdict(list)
        
        # Sort agents by role level
        sorted_agents = sorted(
            self.agents.items(), 
            key=lambda x: x[1].role.value, 
            reverse=True
        )
        
        for task_type, context in tasks:
            # Find suitable agents
            suitable_agents = [
                name for name, agent in sorted_agents
                if task_type in agent.available_tasks
            ]
            
            if suitable_agents:
                # Assign to most appropriate agent (highest rank that can do it)
                assigned_to = suitable_agents[0]
                
                # Add other suitable agents to context for collaboration
                context['other_agents'] = suitable_agents[1:]
                assignments[assigned_to].append((task_type, context))
            else:
                logger.warning(f"No suitable agent for task {task_type.function_name}")
        
        return assignments
    
    async def _process_with_messages(
        self,
        task_assignments: Dict[str, List[Tuple[TaskType, Dict]]],
        duration_seconds: int
    ) -> List[TaskExecution]:
        """Process tasks with inter-agent messaging"""
        results = []
        end_time = time.time() + duration_seconds
        
        # Head chef announces tasks
        head_chef = self._get_head_chef()
        if head_chef:
            for agent_name, tasks in task_assignments.items():
                for task_type, _ in tasks:
                    message = head_chef.send_message(
                        agent_name,
                        f"Please execute {task_type.function_name}",
                        task_type
                    )
                    self.message_bus.append(message)
                    self.agents[agent_name].receive_message(message)
        
        # Process tasks and messages
        for agent_name, tasks in task_assignments.items():
            agent = self.agents[agent_name]
            
            for task_type, context in tasks:
                if time.time() > end_time:
                    logger.info("Time limit reached")
                    break
                
                # Process any pending messages first
                self._process_agent_messages(agent)
                
                # Execute task
                execution = agent.process_task(task_type, context, device=agent.device)
                self.execution_history.append(execution)
                results.append(execution)
                
                # Send collaboration messages if needed
                if execution.collaboration_agents:
                    for collab_agent in execution.collaboration_agents:
                        if collab_agent in self.agents:
                            message = agent.send_message(
                                collab_agent,
                                f"Need assistance with {task_type.function_name}",
                                task_type
                            )
                            self.message_bus.append(message)
                            self.agents[collab_agent].receive_message(message)
                
                # Head chef quality check
                if head_chef and agent_name != head_chef.name:
                    if execution.quality_score < 0.7:
                        message = head_chef.send_message(
                            agent_name,
                            f"Quality issue with {task_type.function_name}. Score: {execution.quality_score:.2f}"
                        )
                        self.message_bus.append(message)
                        agent.receive_message(message)
                    
                        agent.authority_compliance *= 0.95
   
        
        return results
    
    def _process_agent_messages(self, agent: LLMAgent):
        """Process messages in agent's queue"""
        while agent.message_queue:
            message = agent.message_queue.pop(0)
     
            if message.role.value > agent.role.value:
                agent.authority_compliance = min(1.0, agent.authority_compliance * 1.02)
            

            if message.requires_response:
                response = agent.send_message(
                    message.sender,
                    f"Acknowledged {message.content}"
                )
                self.message_bus.append(response)
                
    
                if message.sender in self.agents:
                    self.agents[message.sender].receive_message(response)
    
    def _get_head_chef(self) -> Optional[LLMAgent]:
        """Get the head chef agent if exists"""
        for agent in self.agents.values():
            if agent.role == AgentRole.HEAD_CHEF:
                return agent
        return None
    
    def _collect_scenario_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive metrics from scenario execution"""
        agent_metrics = {}
        
        for name, agent in self.agents.items():
            agent_metrics[name] = agent.get_metrics()
        
    
        total_tasks = len(self.execution_history)
        successful_tasks = [e for e in self.execution_history if e.success]
        
        team_metrics = {
            "overall_success_rate": len(successful_tasks) / max(total_tasks, 1),
            "average_quality": sum(e.quality_score for e in successful_tasks) / max(len(successful_tasks), 1),
            "average_reasoning_time": sum(e.reasoning_time for e in self.execution_history) / max(total_tasks, 1),
            "total_messages": len(self.message_bus),
            "unique_collaborations": len(set(
                (e.agent_name, collab) 
                for e in self.execution_history 
                for collab in e.collaboration_agents
            ))
        }
        

        authority_scores = [a.authority_compliance for a in self.agents.values()]
        team_metrics["hierarchy_compliance"] = sum(authority_scores) / len(authority_scores)
        

        messages_by_role = defaultdict(int)
        for message in self.message_bus:
            messages_by_role[message.role.name] += 1
        
        team_metrics["communication_by_role"] = dict(messages_by_role)
        
        return {
            "agents": agent_metrics,
            "team": team_metrics
        }
    
    def reset(self):
        """Reset coordinator for new scenario"""
        self.message_bus.clear()
        self.task_queue.clear()
        self.execution_history.clear()
        self.scenario_start_time = None
        self.scenario_end_time = None
        
        # Reset agent states
        for agent in self.agents.values():
            agent.message_queue.clear()
            agent.sent_messages.clear()
            agent.task_history.clear()
            agent.authority_compliance = 1.0
            agent.collaboration_score = 0.0
    
    def get_execution_trace(self) -> List[Dict]:
        """Get detailed execution trace for analysis"""
        trace = []
        
        # Combine executions and messages chronologically
        for execution in self.execution_history:
            trace.append({
                "type": "execution",
                "timestamp": execution.start_time,
                "agent": execution.agent_name,
                "task": execution.task_type.function_name,
                "success": execution.success,
                "quality": execution.quality_score
            })
        
        for message in self.message_bus:
            trace.append({
                "type": "message",
                "timestamp": message.timestamp,
                "sender": message.sender,
                "recipient": message.recipient,
                "content": message.content[:100]  # Truncate for readability
            })
        
        # Sort by timestamp
        trace.sort(key=lambda x: x["timestamp"])
        return trace