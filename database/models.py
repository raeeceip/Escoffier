"""
Database models using SQLAlchemy ORM for better data relationships and validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Table, Enum, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func
import json

Base = declarative_base()


# Enums for type safety
class KitchenRole(PyEnum):
    """Kitchen roles for agents."""
    EXECUTIVE_CHEF = "executive_chef"
    SOUS_CHEF = "sous_chef"
    CHEF_DE_PARTIE = "chef_de_partie"
    LINE_COOK = "line_cook"
    PREP_COOK = "prep_cook"
    KITCHEN_PORTER = "kitchen_porter"
    EXPEDITER = "expediter"


class KitchenLocation(PyEnum):
    """Kitchen locations/stations."""
    STOCK = "stock"
    PREP = "prep"
    GRILL = "grill"
    SAUTE = "saute"
    BAKING = "baking"
    EXPEDITE = "expedite"
    DISH = "dish"
    COLD_PREP = "cold_prep"


class TaskStatus(PyEnum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(PyEnum):
    """Communication message types."""
    TASK_REQUEST = "task_request"
    STATUS_UPDATE = "status_update"
    COORDINATION = "coordination"
    ALERT = "alert"
    QUESTION = "question"
    RESPONSE = "response"


# Association tables for many-to-many relationships
agent_skills = Table(
    'agent_skills',
    Base.metadata,
    Column('agent_id', Integer, ForeignKey('agents.id'), primary_key=True),
    Column('skill_id', Integer, ForeignKey('skills.id'), primary_key=True)
)

recipe_ingredients = Table(
    'recipe_ingredients',
    Base.metadata,
    Column('recipe_id', Integer, ForeignKey('recipes.id'), primary_key=True),
    Column('ingredient_id', Integer, ForeignKey('ingredients.id'), primary_key=True),
    Column('quantity', Float, nullable=False),
    Column('unit', String(50), nullable=False),
    Column('preparation', String(100))
)


class Agent(Base):
    """Agent model representing kitchen staff."""
    
    __tablename__ = 'agents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    role = Column(Enum(KitchenRole), nullable=False)
    
    # LLM Configuration
    model_provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    
    # Status and State
    is_active = Column(Boolean, default=True)
    current_location = Column(Enum(KitchenLocation), nullable=True)
    assigned_station = Column(String(100))
    
    # Experience and Skills
    experience_level = Column(Integer, default=0)  # 0-100
    stress_level = Column(Float, default=0.0)  # 0.0-1.0
    performance_rating = Column(Float, default=0.8)  # 0.0-1.0
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    skills = relationship("Skill", secondary=agent_skills, back_populates="agents")
    tasks = relationship("Task", back_populates="agent")
    actions = relationship("AgentAction", back_populates="agent")
    sent_messages = relationship("Communication", foreign_keys="Communication.sender_id", back_populates="sender")
    received_messages = relationship("Communication", foreign_keys="Communication.receiver_id", back_populates="receiver")
    
    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}', role='{self.role.value}')>"


class Skill(Base):
    """Skills that agents can possess."""
    
    __tablename__ = 'skills'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    category = Column(String(50))  # cooking, management, communication, etc.
    difficulty = Column(Integer, default=1)  # 1-10
    
    # Relationships
    agents = relationship("Agent", secondary=agent_skills, back_populates="skills")
    
    def __repr__(self) -> str:
        return f"<Skill(id={self.id}, name='{self.name}')>"


class Ingredient(Base):
    """Ingredient inventory and information."""
    
    __tablename__ = 'ingredients'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    quantity = Column(Float, default=0.0)
    unit = Column(String(50), nullable=False)
    storage_location = Column(Enum(KitchenLocation), default=KitchenLocation.STOCK)
    
    # Quality and freshness
    quality = Column(Float, default=100.0)  # 0-100
    expiration_date = Column(DateTime, nullable=True)
    
    # Metadata
    cost_per_unit = Column(Float, default=0.0)
    supplier = Column(String(100))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    recipes = relationship("Recipe", secondary=recipe_ingredients, back_populates="ingredients")
    
    def __repr__(self) -> str:
        return f"<Ingredient(id={self.id}, name='{self.name}', quantity={self.quantity})>"


class Recipe(Base):
    """Recipe information and instructions."""
    
    __tablename__ = 'recipes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    source = Column(String(100))
    link = Column(Text)
    
    # Recipe content
    directions = Column(JSON)  # List of instruction steps
    ner_entities = Column(JSON)  # Named entity recognition data
    
    # Metadata
    difficulty = Column(Integer, default=1)  # 1-10
    prep_time = Column(Integer, default=0)  # minutes
    cook_time = Column(Integer, default=0)  # minutes
    servings = Column(Integer, default=1)
    
    # Analysis data
    cooking_methods = Column(JSON)  # Extracted cooking methods
    required_skills = Column(JSON)  # Skills needed
    equipment = Column(JSON)  # Required equipment
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    ingredients = relationship("Ingredient", secondary=recipe_ingredients, back_populates="recipes")
    tasks = relationship("Task", back_populates="recipe")
    
    def __repr__(self) -> str:
        return f"<Recipe(id={self.id}, title='{self.title}')>"


class Task(Base):
    """Tasks assigned to agents."""
    
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(Integer, default=5)  # 1-10, higher = more urgent
    
    # Assignment
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id'), nullable=True)
    
    # Execution details
    status = Column(String(20), default="pending")
    estimated_duration = Column(Integer, default=10)  # minutes
    actual_duration = Column(Integer, nullable=True)
    
    # Dependencies
    dependencies = Column(JSON)  # List of task IDs that must complete first
    parameters = Column(JSON)  # Task-specific parameters
    
    # Quality targets
    quality_targets = Column(JSON)  # Expected quality metrics
    actual_quality = Column(JSON, nullable=True)  # Measured quality metrics
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="tasks")
    recipe = relationship("Recipe", back_populates="tasks")
    actions = relationship("AgentAction", back_populates="task")
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, type='{self.task_type}', status='{self.status}')>"


class AgentAction(Base):
    """Individual actions taken by agents."""
    
    __tablename__ = 'agent_actions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=False)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)
    
    # Action details
    action_type = Column(String(100), nullable=False)
    description = Column(Text)
    location = Column(Enum(KitchenLocation), nullable=True)
    
    # Execution
    duration = Column(Integer, default=0)  # seconds
    success = Column(Boolean, default=True)
    quality_score = Column(Float, nullable=True)  # 0-1
    
    # LLM interaction
    llm_prompt = Column(Text, nullable=True)
    llm_response = Column(Text, nullable=True)
    llm_tokens_used = Column(Integer, default=0)
    
    # Context and parameters
    context = Column(JSON)  # Action context and parameters
    result = Column(JSON, nullable=True)  # Action results
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="actions")
    task = relationship("Task", back_populates="actions")
    
    def __repr__(self) -> str:
        return f"<AgentAction(id={self.id}, type='{self.action_type}', agent_id={self.agent_id})>"


class Communication(Base):
    """Communication between agents."""
    
    __tablename__ = 'communications'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(Integer, ForeignKey('agents.id'), nullable=False)
    receiver_id = Column(Integer, ForeignKey('agents.id'), nullable=True)  # None for broadcast
    
    # Message details
    message_type = Column(Enum(MessageType), nullable=False)
    subject = Column(String(200))
    content = Column(Text, nullable=False)
    
    # Context
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)
    priority = Column(Integer, default=5)  # 1-10
    
    # Status
    is_read = Column(Boolean, default=False)
    requires_response = Column(Boolean, default=False)
    response_id = Column(Integer, ForeignKey('communications.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    sender = relationship("Agent", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("Agent", foreign_keys=[receiver_id], back_populates="received_messages")
    response = relationship("Communication", remote_side=[id])
    
    def __repr__(self) -> str:
        return f"<Communication(id={self.id}, type='{self.message_type.value}', sender_id={self.sender_id})>"


class Scenario(Base):
    """Test scenarios for evaluation."""
    
    __tablename__ = 'scenarios'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Configuration
    config = Column(JSON)  # Scenario configuration
    agents_config = Column(JSON)  # Agent setup for scenario
    objectives = Column(JSON)  # Success criteria
    
    # Execution
    status = Column(String(50), default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results
    results = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<Scenario(id={self.id}, name='{self.name}', status='{self.status}')>"


class MetricsSnapshot(Base):
    """Periodic snapshots of system metrics."""
    
    __tablename__ = 'metrics_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # System metrics
    total_agents = Column(Integer, default=0)
    active_agents = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    
    # Performance metrics
    avg_task_completion_time = Column(Float, default=0.0)
    avg_quality_score = Column(Float, default=0.0)
    avg_coordination_score = Column(Float, default=0.0)
    
    # Communication metrics
    messages_sent = Column(Integer, default=0)
    avg_response_time = Column(Float, default=0.0)
    
    # Detailed metrics
    agent_metrics = Column(JSON)  # Per-agent metrics
    task_metrics = Column(JSON)  # Task type metrics
    system_metrics = Column(JSON)  # System-wide metrics
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    def __repr__(self) -> str:
        return f"<MetricsSnapshot(id={self.id}, period={self.period_start}-{self.period_end})>"


# Indexes for performance
Index('idx_agent_role', Agent.role)
Index('idx_agent_active', Agent.is_active)
Index('idx_task_status', Task.status)
Index('idx_task_agent', Task.agent_id)
Index('idx_action_agent', AgentAction.agent_id)
Index('idx_action_task', AgentAction.task_id)
Index('idx_communication_sender', Communication.sender_id)
Index('idx_communication_receiver', Communication.receiver_id)
Index('idx_metrics_created', MetricsSnapshot.created_at)