"""
Recipe-based Task Generator for Kitchen Scenarios
Generates appropriate tasks for different chef roles based on recipe complexity
"""
import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import re

from escoffier_types import AgentType, DifficultyLevel

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


class CookingTechnique(Enum):
    """Cooking techniques that affect task assignment"""
    PREP = "prep"
    KNIFE_WORK = "knife_work"
    SAUTEING = "sauteing"
    GRILLING = "grilling"
    BAKING = "baking"
    ROASTING = "roasting"
    BRAISING = "braising"
    SAUCE_MAKING = "sauce_making"
    PLATING = "plating"
    SEASONING = "seasoning"
    TEMPERATURE_CONTROL = "temperature_control"


@dataclass
class RecipeTask:
    """A task generated from a recipe step"""
    description: str
    agent_type: AgentType
    complexity: TaskComplexity
    estimated_time: int  # minutes
    required_skills: List[str]
    ingredients_needed: List[str]
    equipment_needed: List[str]
    technique: CookingTechnique
    priority: int  # 1-10, higher = more urgent
    dependencies: List[int] = None  # task IDs that must complete first
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'description': self.description,
            'type': 'cooking',
            'agent_type': self.agent_type.value,
            'complexity': self.complexity.value,
            'duration_minutes': self.estimated_time,
            'required_skills': self.required_skills,
            'ingredients': self.ingredients_needed,
            'equipment': self.equipment_needed,
            'technique': self.technique.value,
            'priority': self.priority,
            'dependencies': self.dependencies or [],
            'parameters': {
                'complexity': self.complexity.value,
                'technique': self.technique.value
            }
        }


class RecipeTaskGenerator:
    """Generates cooking tasks from recipes based on agent roles and complexity"""
    
    def __init__(self):
        self.prep_patterns = [
            r'chop|dice|mince|slice|julienne|brunoise',
            r'peel|trim|clean|wash|rinse',
            r'measure|weigh|portion'
        ]
        
        self.cooking_patterns = [
            r'sauté|pan.fry|fry|cook.*until',
            r'grill|broil|char',
            r'bake|roast|oven',
            r'simmer|boil|reduce|braise',
            r'whisk|mix|combine|fold'
        ]
        
        self.plating_patterns = [
            r'serve|plate|garnish|present',
            r'arrange|drizzle|sprinkle'
        ]
        
        # Skill mappings for different agent types
        self.agent_skills = {
            AgentType.HEAD_CHEF: [
                'menu_planning', 'quality_control', 'sauce_making', 'advanced_techniques',
                'leadership', 'cost_control', 'plating', 'seasoning_mastery'
            ],
            AgentType.SOUS_CHEF: [
                'station_management', 'knife_skills', 'sauce_making', 'cooking_techniques',
                'quality_control', 'training', 'inventory_management'
            ],
            AgentType.LINE_COOK: [
                'station_cooking', 'basic_techniques', 'speed_cooking', 'timing',
                'equipment_operation', 'temperature_control'
            ],
            AgentType.PREP_COOK: [
                'knife_skills', 'ingredient_prep', 'basic_cooking', 'organization',
                'food_safety', 'portioning'
            ]
        }
    
    def generate_tasks_from_recipe(self, recipe_data: Dict[str, Any], 
                                 difficulty: DifficultyLevel = DifficultyLevel.MEDIUM) -> List[RecipeTask]:
        """Generate cooking tasks from a recipe"""
        tasks = []
        
        # Parse recipe data
        title = recipe_data.get('title', 'Unknown Recipe')
        ingredients = self._parse_ingredients(recipe_data.get('ingredients', []))
        directions = self._parse_directions(recipe_data.get('directions', []))
        
        # Generate prep tasks
        prep_tasks = self._generate_prep_tasks(ingredients, difficulty)
        tasks.extend(prep_tasks)
        
        # Generate cooking tasks
        cooking_tasks = self._generate_cooking_tasks(directions, ingredients, difficulty)
        tasks.extend(cooking_tasks)
        
        # Generate plating tasks
        plating_tasks = self._generate_plating_tasks(title, difficulty)
        tasks.extend(plating_tasks)
        
        # Set task dependencies
        self._set_task_dependencies(tasks)
        
        logger.info(f"Generated {len(tasks)} tasks for recipe: {title}")
        return tasks
    
    def _parse_ingredients(self, ingredients_raw: Any) -> List[str]:
        """Parse ingredients from various formats"""
        if isinstance(ingredients_raw, str):
            try:
                ingredients = json.loads(ingredients_raw)
            except json.JSONDecodeError:
                ingredients = [ingredients_raw]
        elif isinstance(ingredients_raw, list):
            ingredients = ingredients_raw
        else:
            ingredients = []
        
        return [str(ing).strip() for ing in ingredients]
    
    def _parse_directions(self, directions_raw: Any) -> List[str]:
        """Parse cooking directions from various formats"""
        if isinstance(directions_raw, str):
            try:
                directions = json.loads(directions_raw)
            except json.JSONDecodeError:
                directions = [directions_raw]
        elif isinstance(directions_raw, list):
            directions = directions_raw
        else:
            directions = []
        
        return [str(step).strip() for step in directions]
    
    def _generate_prep_tasks(self, ingredients: List[str], 
                           difficulty: DifficultyLevel) -> List[RecipeTask]:
        """Generate ingredient preparation tasks"""
        prep_tasks = []
        
        # Group ingredients by prep type
        knife_work_ingredients = []
        basic_prep_ingredients = []
        
        for ingredient in ingredients:
            ingredient_lower = ingredient.lower()
            if any(keyword in ingredient_lower for keyword in ['chop', 'dice', 'slice', 'mince']):
                knife_work_ingredients.append(ingredient)
            elif any(keyword in ingredient_lower for keyword in ['peel', 'trim', 'clean', 'wash']):
                basic_prep_ingredients.append(ingredient)
            else:
                basic_prep_ingredients.append(ingredient)
        
        # Generate knife work tasks (for prep cooks or sous chefs)
        if knife_work_ingredients:
            complexity = TaskComplexity.MODERATE if difficulty == DifficultyLevel.HARD else TaskComplexity.SIMPLE
            agent_type = AgentType.SOUS_CHEF if complexity == TaskComplexity.MODERATE else AgentType.PREP_COOK
            
            task = RecipeTask(
                description=f"Perform knife work: {', '.join(knife_work_ingredients[:3])}{'...' if len(knife_work_ingredients) > 3 else ''}",
                agent_type=agent_type,
                complexity=complexity,
                estimated_time=5 + len(knife_work_ingredients) * 2,
                required_skills=['knife_skills', 'ingredient_prep'],
                ingredients_needed=knife_work_ingredients,
                equipment_needed=['chef_knife', 'cutting_board'],
                technique=CookingTechnique.KNIFE_WORK,
                priority=8  # High priority - other tasks depend on prep
            )
            prep_tasks.append(task)
        
        # Generate basic prep tasks
        if basic_prep_ingredients:
            task = RecipeTask(
                description=f"Prepare ingredients: {', '.join(basic_prep_ingredients[:3])}{'...' if len(basic_prep_ingredients) > 3 else ''}",
                agent_type=AgentType.PREP_COOK,
                complexity=TaskComplexity.SIMPLE,
                estimated_time=3 + len(basic_prep_ingredients),
                required_skills=['ingredient_prep', 'organization'],
                ingredients_needed=basic_prep_ingredients,
                equipment_needed=['prep_bowls', 'measuring_tools'],
                technique=CookingTechnique.PREP,
                priority=7
            )
            prep_tasks.append(task)
        
        return prep_tasks
    
    def _generate_cooking_tasks(self, directions: List[str], ingredients: List[str],
                              difficulty: DifficultyLevel) -> List[RecipeTask]:
        """Generate cooking tasks from recipe directions"""
        cooking_tasks = []
        
        for i, step in enumerate(directions):
            step_lower = step.lower()
            
            # Determine cooking technique and complexity
            technique, complexity, agent_type = self._analyze_cooking_step(step_lower, difficulty)
            
            # Extract equipment and ingredients mentioned in step
            equipment = self._extract_equipment(step_lower)
            step_ingredients = self._extract_ingredients_from_step(step, ingredients)
            
            # Estimate time based on step content
            estimated_time = self._estimate_cooking_time(step_lower, technique)
            
            # Get required skills
            required_skills = self._get_required_skills(technique, agent_type)
            
            task = RecipeTask(
                description=step,
                agent_type=agent_type,
                complexity=complexity,
                estimated_time=estimated_time,
                required_skills=required_skills,
                ingredients_needed=step_ingredients,
                equipment_needed=equipment,
                technique=technique,
                priority=5 + i  # Sequential priority
            )
            cooking_tasks.append(task)
        
        return cooking_tasks
    
    def _generate_plating_tasks(self, recipe_title: str, 
                              difficulty: DifficultyLevel) -> List[RecipeTask]:
        """Generate plating and presentation tasks"""
        plating_tasks = []
        
        # Basic plating task
        complexity = TaskComplexity.COMPLEX if difficulty == DifficultyLevel.HARD else TaskComplexity.MODERATE
        agent_type = AgentType.HEAD_CHEF if complexity == TaskComplexity.COMPLEX else AgentType.SOUS_CHEF
        
        task = RecipeTask(
            description=f"Plate and present {recipe_title}",
            agent_type=agent_type,
            complexity=complexity,
            estimated_time=3 if complexity == TaskComplexity.MODERATE else 5,
            required_skills=['plating', 'presentation', 'quality_control'],
            ingredients_needed=[],
            equipment_needed=['plates', 'plating_tools'],
            technique=CookingTechnique.PLATING,
            priority=2  # Low priority - happens at the end
        )
        plating_tasks.append(task)
        
        return plating_tasks
    
    def _analyze_cooking_step(self, step: str, difficulty: DifficultyLevel) -> Tuple[CookingTechnique, TaskComplexity, AgentType]:
        """Analyze a cooking step to determine technique, complexity, and appropriate agent"""
        
        # Map cooking words to techniques
        if any(word in step for word in ['sauté', 'pan', 'fry']):
            technique = CookingTechnique.SAUTEING
            complexity = TaskComplexity.MODERATE
            agent_type = AgentType.LINE_COOK
        elif any(word in step for word in ['grill', 'broil', 'char']):
            technique = CookingTechnique.GRILLING
            complexity = TaskComplexity.MODERATE
            agent_type = AgentType.LINE_COOK
        elif any(word in step for word in ['bake', 'oven', 'roast']):
            technique = CookingTechnique.BAKING
            complexity = TaskComplexity.SIMPLE
            agent_type = AgentType.LINE_COOK
        elif any(word in step for word in ['sauce', 'reduce', 'emulsify']):
            technique = CookingTechnique.SAUCE_MAKING
            complexity = TaskComplexity.COMPLEX
            agent_type = AgentType.SOUS_CHEF
        elif any(word in step for word in ['braise', 'slow', 'confit']):
            technique = CookingTechnique.BRAISING
            complexity = TaskComplexity.EXPERT
            agent_type = AgentType.HEAD_CHEF
        elif any(word in step for word in ['season', 'taste', 'adjust']):
            technique = CookingTechnique.SEASONING
            complexity = TaskComplexity.COMPLEX
            agent_type = AgentType.SOUS_CHEF
        else:
            technique = CookingTechnique.TEMPERATURE_CONTROL
            complexity = TaskComplexity.SIMPLE
            agent_type = AgentType.LINE_COOK
        
        # Adjust based on difficulty
        if difficulty == DifficultyLevel.HARD:
            if complexity == TaskComplexity.SIMPLE:
                complexity = TaskComplexity.MODERATE
            elif complexity == TaskComplexity.MODERATE:
                complexity = TaskComplexity.COMPLEX
                if agent_type == AgentType.LINE_COOK:
                    agent_type = AgentType.SOUS_CHEF
        
        return technique, complexity, agent_type
    
    def _extract_equipment(self, step: str) -> List[str]:
        """Extract equipment mentioned in cooking step"""
        equipment_map = {
            'pan': ['sauté_pan'],
            'pot': ['sauce_pot'],
            'oven': ['oven'],
            'grill': ['grill'],
            'whisk': ['whisk'],
            'spatula': ['spatula'],
            'knife': ['chef_knife'],
            'bowl': ['mixing_bowl'],
            'skillet': ['skillet'],
            'sheet': ['baking_sheet']
        }
        
        equipment = []
        for keyword, items in equipment_map.items():
            if keyword in step:
                equipment.extend(items)
        
        return list(set(equipment))  # Remove duplicates
    
    def _extract_ingredients_from_step(self, step: str, all_ingredients: List[str]) -> List[str]:
        """Extract ingredients mentioned in a specific step"""
        step_ingredients = []
        for ingredient in all_ingredients:
            # Simple check if ingredient or its base form is mentioned
            ingredient_words = ingredient.lower().split()
            if any(word in step.lower() for word in ingredient_words):
                step_ingredients.append(ingredient)
        
        return step_ingredients
    
    def _estimate_cooking_time(self, step: str, technique: CookingTechnique) -> int:
        """Estimate cooking time based on step content and technique"""
        time_patterns = {
            r'(\d+)\s*min': lambda m: int(m.group(1)),
            r'(\d+)\s*hour': lambda m: int(m.group(1)) * 60,
            r'until.*done': lambda m: 10,
            r'until.*tender': lambda m: 15,
            r'until.*brown': lambda m: 5
        }
        
        # Look for explicit time mentions
        for pattern, time_func in time_patterns.items():
            match = re.search(pattern, step)
            if match:
                return time_func(match)
        
        # Default times based on technique
        default_times = {
            CookingTechnique.PREP: 5,
            CookingTechnique.KNIFE_WORK: 8,
            CookingTechnique.SAUTEING: 7,
            CookingTechnique.GRILLING: 10,
            CookingTechnique.BAKING: 25,
            CookingTechnique.ROASTING: 30,
            CookingTechnique.BRAISING: 45,
            CookingTechnique.SAUCE_MAKING: 15,
            CookingTechnique.PLATING: 3,
            CookingTechnique.SEASONING: 2,
            CookingTechnique.TEMPERATURE_CONTROL: 8
        }
        
        return default_times.get(technique, 10)
    
    def _get_required_skills(self, technique: CookingTechnique, agent_type: AgentType) -> List[str]:
        """Get required skills based on technique and agent type"""
        base_skills = self.agent_skills.get(agent_type, [])
        
        technique_skills = {
            CookingTechnique.KNIFE_WORK: ['knife_skills'],
            CookingTechnique.SAUTEING: ['sauteing', 'temperature_control'],
            CookingTechnique.GRILLING: ['grilling', 'temperature_control'],
            CookingTechnique.BAKING: ['baking', 'timing'],
            CookingTechnique.SAUCE_MAKING: ['sauce_making', 'seasoning'],
            CookingTechnique.PLATING: ['plating', 'presentation'],
            CookingTechnique.SEASONING: ['seasoning', 'tasting']
        }
        
        specific_skills = technique_skills.get(technique, [])
        return list(set(base_skills + specific_skills))
    
    def _set_task_dependencies(self, tasks: List[RecipeTask]):
        """Set up task dependencies based on cooking logic"""
        prep_tasks = [i for i, task in enumerate(tasks) if task.technique in [CookingTechnique.PREP, CookingTechnique.KNIFE_WORK]]
        cooking_tasks = [i for i, task in enumerate(tasks) if task.technique not in [CookingTechnique.PREP, CookingTechnique.KNIFE_WORK, CookingTechnique.PLATING]]
        plating_tasks = [i for i, task in enumerate(tasks) if task.technique == CookingTechnique.PLATING]
        
        # Cooking tasks depend on prep tasks
        for cooking_idx in cooking_tasks:
            tasks[cooking_idx].dependencies = prep_tasks
        
        # Plating tasks depend on cooking tasks
        for plating_idx in plating_tasks:
            tasks[plating_idx].dependencies = prep_tasks + cooking_tasks

    def get_tasks_for_scenario(self, recipe_titles: List[str], scenario_type: str, 
                             difficulty: DifficultyLevel = DifficultyLevel.MEDIUM) -> List[Dict[str, Any]]:
        """Generate tasks for multiple recipes in a scenario context"""
        # This would integrate with the recipe manager to get full recipe data
        # For now, return sample tasks
        all_tasks = []
        
        # Add scenario-specific tasks
        if scenario_type == "service_rush":
            all_tasks.extend(self._generate_service_rush_tasks(difficulty))
        elif scenario_type == "collaboration_test":
            all_tasks.extend(self._generate_collaboration_tasks(difficulty))
        
        return [task.to_dict() for task in all_tasks]
    
    def _generate_service_rush_tasks(self, difficulty: DifficultyLevel) -> List[RecipeTask]:
        """Generate tasks for service rush scenario"""
        tasks = []
        
        # Multiple parallel cooking tasks
        tasks.append(RecipeTask(
            description="Prepare appetizer station for service",
            agent_type=AgentType.LINE_COOK,
            complexity=TaskComplexity.MODERATE,
            estimated_time=10,
            required_skills=['station_cooking', 'speed_cooking'],
            ingredients_needed=['bread', 'spreads', 'garnishes'],
            equipment_needed=['plates', 'spreaders'],
            technique=CookingTechnique.PLATING,
            priority=8
        ))
        
        tasks.append(RecipeTask(
            description="Manage main course grill station",
            agent_type=AgentType.SOUS_CHEF,
            complexity=TaskComplexity.COMPLEX,
            estimated_time=15,
            required_skills=['grilling', 'temperature_control', 'timing'],
            ingredients_needed=['proteins', 'marinades'],
            equipment_needed=['grill', 'tongs', 'thermometer'],
            technique=CookingTechnique.GRILLING,
            priority=9
        ))
        
        return tasks
    
    def _generate_collaboration_tasks(self, difficulty: DifficultyLevel) -> List[RecipeTask]:
        """Generate tasks that require collaboration between agents"""
        tasks = []
        
        # Complex dish requiring coordination
        tasks.append(RecipeTask(
            description="Coordinate multi-course meal preparation",
            agent_type=AgentType.HEAD_CHEF,
            complexity=TaskComplexity.EXPERT,
            estimated_time=20,
            required_skills=['leadership', 'timing', 'quality_control'],
            ingredients_needed=['various'],
            equipment_needed=['full_kitchen'],
            technique=CookingTechnique.TEMPERATURE_CONTROL,
            priority=10
        ))
        
        tasks.append(RecipeTask(
            description="Prepare synchronized sauce components",
            agent_type=AgentType.SOUS_CHEF,
            complexity=TaskComplexity.COMPLEX,
            estimated_time=12,
            required_skills=['sauce_making', 'timing', 'communication'],
            ingredients_needed=['stocks', 'reductions', 'aromatics'],
            equipment_needed=['sauce_pots', 'strainers'],
            technique=CookingTechnique.SAUCE_MAKING,
            priority=8
        ))
        
        return tasks