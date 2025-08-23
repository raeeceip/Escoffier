"""
Recipe Management System - Advanced recipe processing with pandas
"""
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set
from pathlib import Path
import json
import csv
import re
from enum import Enum

from config import Config
from database.models import Recipe, Ingredient
from database import DatabaseManager
from escoffier_types import DifficultyLevel, RecipeType, CuisineType

logger = logging.getLogger(__name__)


class NutrientType(Enum):
    """Nutrient types for analysis"""
    CALORIES = "calories"
    PROTEIN = "protein"
    CARBS = "carbohydrates"
    FAT = "fat"
    FIBER = "fiber"
    SODIUM = "sodium"
    SUGAR = "sugar"


@dataclass
class NutritionInfo:
    """Nutrition information for recipes"""
    calories: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    sodium_mg: float = 0.0
    sugar_g: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'calories': self.calories,
            'protein_g': self.protein_g,
            'carbs_g': self.carbs_g,
            'fat_g': self.fat_g,
            'fiber_g': self.fiber_g,
            'sodium_mg': self.sodium_mg,
            'sugar_g': self.sugar_g
        }


@dataclass
class RecipeStep:
    """Individual recipe step"""
    step_number: int
    instruction: str
    duration_minutes: float
    temperature: Optional[int] = None
    equipment: Optional[str] = None
    techniques: List[str] = None
    
    def __post_init__(self):
        if self.equipment is None:
            self.equipment = []
        if self.techniques is None:
            self.techniques = []


@dataclass
class RecipeIngredient:
    """Recipe ingredient with quantity and preparation"""
    name: str
    quantity: float
    unit: str
    preparation: Optional[str] = None
    substitutes: List[str] = None
    
    def __post_init__(self):
        if self.substitutes is None:
            self.substitutes = []


class RecipeManager:
    """Advanced recipe management with pandas processing"""
    
    def __init__(self, config: Config, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.recipes_df: Optional[pd.DataFrame] = None
        self.ingredients_df: Optional[pd.DataFrame] = None
        self.nutrition_df: Optional[pd.DataFrame] = None
        self.recipe_cache: Dict[str, Dict] = {}
        
        # Recipe processing patterns
        self.quantity_patterns = [
            r'(\d+(?:\.\d+)?)\s*(cups?|tablespoons?|teaspoons?|lbs?|ounces?|grams?|kg|ml|l)',
            r'(\d+(?:\.\d+)?)\s*(tbsp|tsp|oz|g|kg|ml|l)',
            r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)'
        ]
        
        # Technique keywords
        self.cooking_techniques = {
            'sauté', 'sear', 'braise', 'roast', 'bake', 'grill', 'steam', 'boil',
            'simmer', 'fry', 'deep-fry', 'stir-fry', 'poach', 'blanch', 'marinate',
            'reduce', 'whisk', 'fold', 'knead', 'dice', 'mince', 'julienne', 'chop'
        }
        
    async def initialize(self):
        """Initialize recipe manager and load data"""
        await self.load_recipes_from_csv()
        await self.load_ingredients_data()
        await self.build_nutrition_database()
        logger.info("Recipe manager initialized")
        
    async def load_recipes_from_csv(self, csv_path: Optional[str] = None):
        """Load recipes from CSV file using pandas"""
        if csv_path is None:
            csv_path = self.config.data_dir / "sample_recipes.csv"
            
        try:
            if Path(csv_path).exists():
                # Load with pandas for powerful data processing
                self.recipes_df = pd.read_csv(csv_path)
                
                # Clean and standardize data
                self.recipes_df = self._clean_recipe_data(self.recipes_df)
                
                # Cache processed recipes
                await self._cache_processed_recipes()
                
                logger.info(f"Loaded {len(self.recipes_df)} recipes from {csv_path}")
            else:
                logger.warning(f"Recipe CSV file not found: {csv_path}")
                self.recipes_df = pd.DataFrame(columns=[
                    'id', 'name', 'cuisine', 'difficulty', 'prep_time', 'cook_time',
                    'servings', 'ingredients', 'instructions', 'techniques', 'equipment'
                ])
                
        except Exception as e:
            logger.error(f"Failed to load recipes from CSV: {e}")
            self.recipes_df = pd.DataFrame()
            
    def _clean_recipe_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize recipe data"""
        # Handle missing values
        df = df.fillna({
            'cuisine': 'unknown',
            'difficulty': 'medium',
            'prep_time': 30,
            'cook_time': 30,
            'servings': 4,
            'ingredients': '[]',
            'instructions': '[]',
            'techniques': '[]',
            'equipment': '[]'
        })
        
        # Standardize cuisine types
        cuisine_mapping = {
            'italian': 'italian',
            'french': 'french',
            'chinese': 'chinese',
            'japanese': 'japanese',
            'indian': 'indian',
            'mexican': 'mexican',
            'american': 'american',
            'mediterranean': 'mediterranean',
        }
        df['cuisine'] = df['cuisine'].str.lower().map(cuisine_mapping).fillna('international')
        
        # Standardize difficulty levels
        difficulty_mapping = {
            'easy': 'easy',
            'beginner': 'easy',
            'medium': 'medium',
            'intermediate': 'medium',
            'hard': 'hard',
            'difficult': 'hard',
            'expert': 'hard'
        }
        df['difficulty'] = df['difficulty'].str.lower().map(difficulty_mapping).fillna('medium')
        
        # Ensure numeric types
        df['prep_time'] = pd.to_numeric(df['prep_time'], errors='coerce').fillna(30)
        df['cook_time'] = pd.to_numeric(df['cook_time'], errors='coerce').fillna(30)
        df['servings'] = pd.to_numeric(df['servings'], errors='coerce').fillna(4)
        
        # Parse JSON columns safely
        for col in ['ingredients', 'instructions', 'techniques', 'equipment']:
            if col in df.columns:
                df[col] = df[col].apply(self._safe_json_parse)
                
        return df
        
    def _safe_json_parse(self, value: str) -> List:
        """Safely parse JSON string to list"""
        if pd.isna(value) or value == '':
            return []
        try:
            if isinstance(value, str):
                # Handle common CSV formatting issues
                value = value.replace("'", '"')
                return json.loads(value)
            elif isinstance(value, list):
                return value
            else:
                return []
        except (json.JSONDecodeError, TypeError):
            # If JSON parsing fails, try to split by common delimiters
            if isinstance(value, str):
                return [item.strip() for item in re.split(r'[,;|]', value) if item.strip()]
            return []
            
    async def _cache_processed_recipes(self):
        """Cache processed recipes for faster access"""
        self.recipe_cache.clear()
        
        for _, row in self.recipes_df.iterrows():
            recipe_data = {
                'id': row['id'] if 'id' in row else row.name,
                'name': row['name'],
                'cuisine': row['cuisine'],
                'difficulty': row['difficulty'],
                'prep_time': row['prep_time'],
                'cook_time': row['cook_time'],
                'total_time': row['prep_time'] + row['cook_time'],
                'servings': row['servings'],
                'ingredients': self._parse_ingredients(row['ingredients']),
                'instructions': self._parse_instructions(row['instructions']),
                'techniques': row['techniques'],
                'equipment': row['equipment'],
                'nutrition': self._estimate_nutrition(row)
            }
            
            self.recipe_cache[str(recipe_data['id'])] = recipe_data
            
    def _parse_ingredients(self, ingredients_data: List) -> List[RecipeIngredient]:
        """Parse ingredient data into structured format"""
        parsed_ingredients = []
        
        for ingredient in ingredients_data:
            if isinstance(ingredient, str):
                # Parse string format: "2 cups flour"
                parsed = self._parse_ingredient_string(ingredient)
                parsed_ingredients.append(parsed)
            elif isinstance(ingredient, dict):
                # Already structured
                parsed_ingredients.append(RecipeIngredient(
                    name=ingredient.get('name', ''),
                    quantity=ingredient.get('quantity', 1.0),
                    unit=ingredient.get('unit', ''),
                    preparation=ingredient.get('preparation'),
                    substitutes=ingredient.get('substitutes', [])
                ))
                
        return parsed_ingredients
        
    def _parse_ingredient_string(self, ingredient_str: str) -> RecipeIngredient:
        """Parse ingredient string into structured format"""
        # Try to match quantity patterns
        for pattern in self.quantity_patterns:
            match = re.match(pattern, ingredient_str.strip(), re.IGNORECASE)
            if match:
                quantity = float(match.group(1))
                unit = match.group(2).lower()
                name = ingredient_str[match.end():].strip()
                
                # Extract preparation method if present
                prep_match = re.search(r',\s*(.+)', name)
                preparation = prep_match.group(1) if prep_match else None
                if preparation:
                    name = name[:prep_match.start()]
                    
                return RecipeIngredient(
                    name=name.strip(),
                    quantity=quantity,
                    unit=unit,
                    preparation=preparation
                )
                
        # Fallback for unparseable ingredients
        return RecipeIngredient(
            name=ingredient_str.strip(),
            quantity=1.0,
            unit='item'
        )
        
    def _parse_instructions(self, instructions_data: List) -> List[RecipeStep]:
        """Parse instruction data into structured steps"""
        parsed_steps = []
        
        for i, instruction in enumerate(instructions_data):
            if isinstance(instruction, str):
                step = RecipeStep(
                    step_number=i + 1,
                    instruction=instruction,
                    duration_minutes=self._extract_duration(instruction),
                    temperature=self._extract_temperature(instruction),
                    equipment=self._extract_equipment(instruction),
                    techniques=self._extract_techniques(instruction)
                )
                parsed_steps.append(step)
            elif isinstance(instruction, dict):
                step = RecipeStep(
                    step_number=instruction.get('step', i + 1),
                    instruction=instruction.get('instruction', ''),
                    duration_minutes=instruction.get('duration', 0),
                    temperature=instruction.get('temperature'),
                    equipment=instruction.get('equipment', []),
                    techniques=instruction.get('techniques', [])
                )
                parsed_steps.append(step)
                
        return parsed_steps
        
    def _extract_duration(self, instruction: str) -> float:
        """Extract cooking duration from instruction text"""
        # Look for time patterns
        time_patterns = [
            r'(\d+(?:\.\d+)?)\s*minutes?',
            r'(\d+(?:\.\d+)?)\s*mins?',
            r'(\d+(?:\.\d+)?)\s*hours?',
            r'(\d+(?:\.\d+)?)\s*hrs?'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, instruction.lower())
            if match:
                duration = float(match.group(1))
                if 'hour' in pattern or 'hr' in pattern:
                    duration *= 60  # Convert to minutes
                return duration
                
        return 0.0
        
    def _extract_temperature(self, instruction: str) -> Optional[int]:
        """Extract temperature from instruction text"""
        temp_patterns = [
            r'(\d+)°?[Ff]',
            r'(\d+)\s*degrees?\s*[Ff]?',
            r'preheat.*?(\d+)'
        ]
        
        for pattern in temp_patterns:
            match = re.search(pattern, instruction)
            if match:
                return int(match.group(1))
                
        return None
        
    def _extract_equipment(self, instruction: str) -> List[str]:
        """Extract equipment from instruction text"""
        equipment_keywords = {
            'oven', 'pan', 'pot', 'skillet', 'baking sheet', 'bowl', 'mixer',
            'blender', 'food processor', 'grill', 'stovetop', 'microwave',
            'dutch oven', 'casserole', 'roasting pan', 'saucepan', 'stockpot'
        }
        
        found_equipment = []
        instruction_lower = instruction.lower()
        
        for equipment in equipment_keywords:
            if equipment in instruction_lower:
                found_equipment.append(equipment)
                
        return found_equipment
        
    def _extract_techniques(self, instruction: str) -> List[str]:
        """Extract cooking techniques from instruction text"""
        found_techniques = []
        instruction_lower = instruction.lower()
        
        for technique in self.cooking_techniques:
            if technique in instruction_lower:
                found_techniques.append(technique)
                
        return found_techniques
        
    def _estimate_nutrition(self, recipe_row: pd.Series) -> NutritionInfo:
        """Estimate nutrition information for recipe"""
        # Simple estimation based on ingredients
        # In a real system, this would use a comprehensive nutrition database
        
        nutrition = NutritionInfo()
        
        # Basic estimates based on common ingredients
        ingredient_calories = {
            'flour': 455,  # per 100g
            'sugar': 387,
            'butter': 717,
            'oil': 884,
            'chicken': 165,
            'beef': 250,
            'rice': 130,
            'pasta': 131,
            'cheese': 350,
            'milk': 42,
            'egg': 155
        }
        
        try:
            ingredients = recipe_row['ingredients']
            if isinstance(ingredients, list):
                for ingredient in ingredients:
                    ingredient_name = ingredient.lower() if isinstance(ingredient, str) else str(ingredient).lower()
                    
                    # Simple matching for common ingredients
                    for name, calories_per_100g in ingredient_calories.items():
                        if name in ingredient_name:
                            # Rough estimate: assume 100g per ingredient mention
                            nutrition.calories += calories_per_100g * 0.5  # Scale down
                            break
                            
        except Exception as e:
            logger.debug(f"Error estimating nutrition: {e}")
            
        # Scale by servings
        servings = recipe_row.get('servings', 4)
        if servings > 0:
            nutrition.calories /= servings
            
        return nutrition
        
    async def load_ingredients_data(self):
        """Load ingredient database for analysis"""
        # Load from database
        with self.db_manager.get_session() as session:
            ingredients = session.query(Ingredient).all()
            
            if ingredients:
                ingredients_data = [{
                    'id': ing.id,
                    'name': ing.name,
                    'category': ing.category,
                    'unit': ing.unit,
                    'cost_per_unit': ing.cost_per_unit,
                    'calories_per_unit': ing.calories_per_unit,
                    'created_at': ing.created_at
                } for ing in ingredients]
                
                self.ingredients_df = pd.DataFrame(ingredients_data)
                logger.info(f"Loaded {len(ingredients)} ingredients from database")
            else:
                # Create empty DataFrame with expected columns
                self.ingredients_df = pd.DataFrame(columns=[
                    'id', 'name', 'category', 'unit', 'cost_per_unit', 'calories_per_unit'
                ])
                
    async def build_nutrition_database(self):
        """Build nutrition analysis database"""
        if self.recipes_df is not None and not self.recipes_df.empty:
            nutrition_data = []
            
            for recipe_id, recipe_data in self.recipe_cache.items():
                nutrition = recipe_data['nutrition']
                nutrition_data.append({
                    'recipe_id': recipe_id,
                    'recipe_name': recipe_data['name'],
                    'cuisine': recipe_data['cuisine'],
                    'difficulty': recipe_data['difficulty'],
                    'servings': recipe_data['servings'],
                    **nutrition.to_dict()
                })
                
            self.nutrition_df = pd.DataFrame(nutrition_data)
            logger.info(f"Built nutrition database for {len(nutrition_data)} recipes")
            
    def search_recipes(
        self,
        query: Optional[str] = None,
        cuisine: Optional[str] = None,
        difficulty: Optional[str] = None,
        max_time: Optional[int] = None,
        ingredients: Optional[List[str]] = None,
        techniques: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Search recipes with multiple filters"""
        if self.recipes_df is None or self.recipes_df.empty:
            return pd.DataFrame()
            
        df = self.recipes_df.copy()
        
        # Text search
        if query:
            mask = (
                df['name'].str.contains(query, case=False, na=False) |
                df['ingredients'].astype(str).str.contains(query, case=False, na=False) |
                df['instructions'].astype(str).str.contains(query, case=False, na=False)
            )
            df = df[mask]
            
        # Cuisine filter
        if cuisine:
            df = df[df['cuisine'].str.lower() == cuisine.lower()]
            
        # Difficulty filter
        if difficulty:
            df = df[df['difficulty'].str.lower() == difficulty.lower()]
            
        # Time filter
        if max_time:
            df = df[(df['prep_time'] + df['cook_time']) <= max_time]
            
        # Ingredient filter
        if ingredients:
            for ingredient in ingredients:
                mask = df['ingredients'].astype(str).str.contains(ingredient, case=False, na=False)
                df = df[mask]
                
        # Technique filter
        if techniques:
            for technique in techniques:
                mask = df['techniques'].astype(str).str.contains(technique, case=False, na=False)
                df = df[mask]
                
        # Ensure we always return a DataFrame, not a Series
        if isinstance(df, pd.Series):
            df = df.to_frame().T
        
        return df
        
    def get_recipe_recommendations(
        self,
        agent_skills: List[str],
        available_ingredients: List[str],
        time_limit: int,
        difficulty_preference: str = 'medium'
    ) -> List[Dict]:
        """Get recipe recommendations based on constraints"""
        if self.recipes_df is None or self.recipes_df.empty:
            return []
            
        # Filter by time and difficulty
        candidates = self.search_recipes(
            difficulty=difficulty_preference,
            max_time=time_limit
        )
        
        if candidates.empty:
            return []
            
        recommendations = []
        
        for _, recipe in candidates.iterrows():
            recipe_id = recipe['id'] if 'id' in recipe else recipe.name
            cached_recipe = self.recipe_cache.get(str(recipe_id))
            
            if not cached_recipe:
                continue
                
            # Calculate match score
            score = self._calculate_recipe_match_score(
                cached_recipe,
                agent_skills,
                available_ingredients
            )
            
            recommendations.append({
                'recipe_id': recipe_id,
                'name': cached_recipe['name'],
                'score': score,
                'difficulty': cached_recipe['difficulty'],
                'total_time': cached_recipe['total_time'],
                'cuisine': cached_recipe['cuisine'],
                'techniques_required': cached_recipe['techniques'],
                'missing_ingredients': self._get_missing_ingredients(
                    cached_recipe['ingredients'],
                    available_ingredients
                )
            })
            
        # Sort by score
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:10]  # Top 10 recommendations
        
    def _calculate_recipe_match_score(
        self,
        recipe: Dict,
        agent_skills: List[str],
        available_ingredients: List[str]
    ) -> float:
        """Calculate how well a recipe matches current constraints"""
        score = 0.0
        
        # Skill match (40% of score)
        required_techniques = set(recipe['techniques'])
        available_skills = set(skill.lower() for skill in agent_skills)
        
        if required_techniques:
            skill_match = len(required_techniques & available_skills) / len(required_techniques)
            score += 0.4 * skill_match
        else:
            score += 0.4  # No special skills required
            
        # Ingredient availability (40% of score)
        required_ingredients = [ing.name.lower() for ing in recipe['ingredients']]
        available_ing_lower = [ing.lower() for ing in available_ingredients]
        
        if required_ingredients:
            ingredient_match = sum(
                1 for ing in required_ingredients
                if any(ing in avail_ing for avail_ing in available_ing_lower)
            ) / len(required_ingredients)
            score += 0.4 * ingredient_match
        else:
            score += 0.4
            
        # Difficulty bonus (20% of score)
        difficulty_bonus = {
            'easy': 1.0,
            'medium': 0.8,
            'hard': 0.6
        }
        score += 0.2 * difficulty_bonus.get(recipe['difficulty'], 0.5)
        
        return score
        
    def _get_missing_ingredients(
        self,
        recipe_ingredients: List[RecipeIngredient],
        available_ingredients: List[str]
    ) -> List[str]:
        """Get list of missing ingredients for a recipe"""
        available_lower = [ing.lower() for ing in available_ingredients]
        missing = []
        
        for recipe_ing in recipe_ingredients:
            found = any(
                recipe_ing.name.lower() in avail_ing.lower()
                for avail_ing in available_lower
            )
            if not found:
                missing.append(recipe_ing.name)
                
        return missing
        
    def analyze_recipe_complexity(self, recipe_id: str) -> Dict:
        """Analyze recipe complexity and requirements"""
        recipe = self.recipe_cache.get(recipe_id)
        if not recipe:
            return {}
            
        complexity = {
            'difficulty_score': self._calculate_difficulty_score(recipe),
            'time_complexity': recipe['total_time'],
            'technique_count': len(recipe['techniques']),
            'ingredient_count': len(recipe['ingredients']),
            'equipment_required': recipe['equipment'],
            'skill_requirements': recipe['techniques'],
            'preparation_steps': len(recipe['instructions'])
        }
        
        return complexity
        
    def _calculate_difficulty_score(self, recipe: Dict) -> float:
        """Calculate numerical difficulty score"""
        base_scores = {
            'easy': 1.0,
            'medium': 2.0,
            'hard': 3.0
        }
        
        score = base_scores.get(recipe['difficulty'], 2.0)
        
        # Adjust based on techniques
        advanced_techniques = {
            'braise', 'reduce', 'julienne', 'brunoise', 'confit', 'sous-vide'
        }
        technique_bonus = sum(
            0.5 for technique in recipe['techniques']
            if technique in advanced_techniques
        )
        
        # Adjust based on time
        time_bonus = min(1.0, recipe['total_time'] / 120)  # 2-hour baseline
        
        return score + technique_bonus + time_bonus
        
    def get_nutrition_analysis(self, recipe_id: str) -> Dict:
        """Get detailed nutrition analysis for recipe"""
        recipe = self.recipe_cache.get(recipe_id)
        if not recipe:
            return {}
            
        nutrition = recipe['nutrition']
        
        analysis = {
            'per_serving': nutrition.to_dict(),
            'total_recipe': {
                key: value * recipe['servings']
                for key, value in nutrition.to_dict().items()
            },
            'nutrition_density': {
                'protein_per_calorie': nutrition.protein_g / max(1, nutrition.calories),
                'fiber_per_calorie': nutrition.fiber_g / max(1, nutrition.calories),
                'sodium_per_calorie': nutrition.sodium_mg / max(1, nutrition.calories)
            },
            'health_score': self._calculate_health_score(nutrition)
        }
        
        return analysis
        
    def _calculate_health_score(self, nutrition: NutritionInfo) -> float:
        """Calculate health score based on nutrition"""
        score = 5.0  # Base score out of 10
        
        # Protein bonus
        if nutrition.protein_g > 20:
            score += 1.0
        elif nutrition.protein_g > 10:
            score += 0.5
            
        # Fiber bonus
        if nutrition.fiber_g > 5:
            score += 1.0
        elif nutrition.fiber_g > 2:
            score += 0.5
            
        # Sodium penalty
        if nutrition.sodium_mg > 1000:
            score -= 1.0
        elif nutrition.sodium_mg > 600:
            score -= 0.5
            
        # Sugar penalty
        if nutrition.sugar_g > 25:
            score -= 1.0
        elif nutrition.sugar_g > 15:
            score -= 0.5
            
        return max(0.0, min(10.0, score))
        
    def export_recipe_data(self, format: str = 'csv', output_path: str = None) -> str:
        """Export recipe data in various formats"""
        if self.recipes_df is None or self.recipes_df.empty:
            raise ValueError("No recipe data to export")
            
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"recipes_export_{timestamp}"
            
        if format.lower() == 'csv':
            output_file = f"{output_path}.csv"
            self.recipes_df.to_csv(output_file, index=False)
        elif format.lower() == 'json':
            output_file = f"{output_path}.json"
            self.recipes_df.to_json(output_file, orient='records', indent=2)
        elif format.lower() == 'excel':
            output_file = f"{output_path}.xlsx"
            with pd.ExcelWriter(output_file) as writer:
                self.recipes_df.to_excel(writer, sheet_name='Recipes', index=False)
                if self.nutrition_df is not None:
                    self.nutrition_df.to_excel(writer, sheet_name='Nutrition', index=False)
                if self.ingredients_df is not None:
                    self.ingredients_df.to_excel(writer, sheet_name='Ingredients', index=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")
            
        logger.info(f"Exported recipe data to {output_file}")
        return output_file
        
    def get_recipe_statistics(self) -> Dict:
        """Get comprehensive recipe statistics"""
        if self.recipes_df is None or self.recipes_df.empty:
            return {}
            
        stats = {
            'total_recipes': len(self.recipes_df),
            'cuisines': self.recipes_df['cuisine'].value_counts().to_dict(),
            'difficulty_distribution': self.recipes_df['difficulty'].value_counts().to_dict(),
            'average_prep_time': self.recipes_df['prep_time'].mean(),
            'average_cook_time': self.recipes_df['cook_time'].mean(),
            'average_total_time': (self.recipes_df['prep_time'] + self.recipes_df['cook_time']).mean(),
            'average_servings': self.recipes_df['servings'].mean(),
            'time_ranges': {
                'quick_meals': len(self.recipes_df[(self.recipes_df['prep_time'] + self.recipes_df['cook_time']) <= 30]),
                'medium_meals': len(self.recipes_df[
                    ((self.recipes_df['prep_time'] + self.recipes_df['cook_time']) > 30) &
                    ((self.recipes_df['prep_time'] + self.recipes_df['cook_time']) <= 60)
                ]),
                'long_meals': len(self.recipes_df[(self.recipes_df['prep_time'] + self.recipes_df['cook_time']) > 60])
            }
        }
        
        if self.nutrition_df is not None and not self.nutrition_df.empty:
            stats['nutrition_stats'] = {
                'average_calories': self.nutrition_df['calories'].mean(),
                'average_protein': self.nutrition_df['protein_g'].mean(),
                'average_carbs': self.nutrition_df['carbs_g'].mean(),
                'average_fat': self.nutrition_df['fat_g'].mean()
            }
            
        return stats