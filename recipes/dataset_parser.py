"""
Dataset Parser for ChefBench
Loads and processes Kaggle recipe dataset for scenario generation
"""

import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import logging
import random
from collections import Counter

logger = logging.getLogger(__name__)


class RecipeDatasetParser:
    """Parse and manage Kaggle recipe dataset"""
    
    def __init__(self, data_path: str = "data"):
        self.data_path = Path(data_path)
        self.recipes: List[Dict[str, str]] = []
        self.ingredients: Dict[str, int] = {}  # ingredient -> frequency
        self.cuisines: List[str] = []
        self.loaded = False
        
    def load_kaggle_dataset(self, file_path: str) -> bool:
        """Load Kaggle recipe JSON dataset"""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"Dataset file not found: {file_path}")
                return False
            
            logger.info(f"Loading dataset from {file_path}")
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Process recipes
            self.recipes = []
            ingredient_counter = Counter()
            cuisine_set = set()
            
            for item in data:
                if isinstance(item, dict):
                    recipe = {
                        'id': item.get('id', len(self.recipes)),
                        'cuisine': item.get('cuisine', 'unknown'),
                        'ingredients': item.get('ingredients', [])
                    }
                    
                    self.recipes.append(recipe)
                    cuisine_set.add(recipe['cuisine'])
                    
                    # Count ingredients
                    for ingredient in recipe['ingredients']:
                        ingredient_counter[ingredient.lower()] += 1
            
            self.ingredients = dict(ingredient_counter)
            self.cuisines = sorted(list(cuisine_set))
            self.loaded = True
            
            logger.info(f"Loaded {len(self.recipes)} recipes with {len(self.ingredients)} unique ingredients")
            logger.info(f"Found {len(self.cuisines)} cuisines")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            return False
    
    def get_random_ingredients(self, count: int = 10, min_frequency: int = 5) -> List[str]:
        """Get random ingredients above minimum frequency threshold"""
        if not self.loaded:
            logger.warning("Dataset not loaded")
            return []
        
        # Filter by frequency
        common_ingredients = [
            ing for ing, freq in self.ingredients.items() 
            if freq >= min_frequency
        ]
        
        if len(common_ingredients) < count:
            return common_ingredients
        
        return random.sample(common_ingredients, count)
    
    def get_recipe_by_ingredients(self, available_ingredients: List[str]) -> Optional[Dict]:
        """Find a recipe that can be made with available ingredients"""
        if not self.loaded:
            return None
        
        available_set = set(ing.lower() for ing in available_ingredients)
        
        # Find recipes where all ingredients are available
        matching_recipes = []
        for recipe in self.recipes:
            recipe_ingredients = set(ing.lower() for ing in recipe['ingredients'])
            if recipe_ingredients.issubset(available_set):
                matching_recipes.append(recipe)
        
        if matching_recipes:
            return random.choice(matching_recipes)
        
        # If no perfect match, find recipe with most ingredients available
        best_match = None
        best_score = 0
        
        for recipe in self.recipes:
            recipe_ingredients = set(ing.lower() for ing in recipe['ingredients'])
            overlap = len(recipe_ingredients.intersection(available_set))
            score = overlap / len(recipe_ingredients) if recipe_ingredients else 0
            
            if score > best_score:
                best_score = score
                best_match = recipe
        
        return best_match
    
    def get_recipes_by_cuisine(self, cuisine: str, count: int = 5) -> List[Dict]:
        """Get random recipes from specific cuisine"""
        if not self.loaded:
            return []
        
        cuisine_recipes = [
            r for r in self.recipes 
            if r['cuisine'].lower() == cuisine.lower()
        ]
        
        if len(cuisine_recipes) <= count:
            return cuisine_recipes
        
        return random.sample(cuisine_recipes, count)
    
    def generate_kitchen_inventory(self, size: str = "medium") -> Dict[str, Any]:
        """Generate a realistic kitchen inventory"""
        if not self.loaded:
            logger.warning("Dataset not loaded, using default inventory")
            return self._default_inventory()
        
        sizes = {
            "small": (20, 30),
            "medium": (40, 60),
            "large": (80, 120)
        }
        
        min_items, max_items = sizes.get(size, (40, 60))
        num_ingredients = random.randint(min_items, max_items)
        
        # Get mix of common and uncommon ingredients
        common = self.get_random_ingredients(int(num_ingredients * 0.7), min_frequency=20)
        uncommon = self.get_random_ingredients(int(num_ingredients * 0.3), min_frequency=5)
        
        ingredients = list(set(common + uncommon))
        
        # Add quantities
        inventory = {}
        for ingredient in ingredients:
            # Common ingredients have higher quantities
            frequency = self.ingredients.get(ingredient.lower(), 1)
            if frequency > 50:
                quantity = random.randint(5, 20)
            elif frequency > 20:
                quantity = random.randint(2, 10)
            else:
                quantity = random.randint(1, 5)
            
            inventory[ingredient] = {
                "quantity": quantity,
                "unit": self._get_unit(ingredient),
                "freshness": random.uniform(0.7, 1.0)
            }
        
        return inventory
    
    def _get_unit(self, ingredient: str) -> str:
        """Get appropriate unit for ingredient"""
        ingredient_lower = ingredient.lower()
        
        if any(x in ingredient_lower for x in ['oil', 'sauce', 'milk', 'cream', 'broth', 'wine']):
            return "ml"
        elif any(x in ingredient_lower for x in ['flour', 'sugar', 'rice', 'pasta']):
            return "g"
        elif any(x in ingredient_lower for x in ['egg', 'onion', 'tomato', 'potato', 'apple']):
            return "pieces"
        elif any(x in ingredient_lower for x in ['salt', 'pepper', 'spice', 'herb']):
            return "tsp"
        else:
            return "units"
    
    def _default_inventory(self) -> Dict[str, Any]:
        """Return default inventory if dataset not loaded"""
        return {
            "salt": {"quantity": 500, "unit": "g", "freshness": 1.0},
            "pepper": {"quantity": 200, "unit": "g", "freshness": 1.0},
            "olive oil": {"quantity": 1000, "unit": "ml", "freshness": 0.9},
            "butter": {"quantity": 500, "unit": "g", "freshness": 0.8},
            "flour": {"quantity": 2000, "unit": "g", "freshness": 0.95},
            "sugar": {"quantity": 1000, "unit": "g", "freshness": 1.0},
            "eggs": {"quantity": 24, "unit": "pieces", "freshness": 0.85},
            "milk": {"quantity": 2000, "unit": "ml", "freshness": 0.75},
            "onions": {"quantity": 10, "unit": "pieces", "freshness": 0.8},
            "garlic": {"quantity": 20, "unit": "cloves", "freshness": 0.9},
            "tomatoes": {"quantity": 15, "unit": "pieces", "freshness": 0.7},
            "chicken breast": {"quantity": 2000, "unit": "g", "freshness": 0.8},
            "ground beef": {"quantity": 1500, "unit": "g", "freshness": 0.85},
            "pasta": {"quantity": 1000, "unit": "g", "freshness": 1.0},
            "rice": {"quantity": 2000, "unit": "g", "freshness": 1.0}
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get dataset statistics"""
        if not self.loaded:
            return {"status": "not_loaded"}
        
        # Ingredient statistics
        ingredient_frequencies = sorted(
            self.ingredients.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Cuisine distribution
        cuisine_counts = Counter(r['cuisine'] for r in self.recipes)
        
        # Recipe complexity (by ingredient count)
        ingredient_counts = [len(r['ingredients']) for r in self.recipes]
        
        return {
            "total_recipes": len(self.recipes),
            "unique_ingredients": len(self.ingredients),
            "unique_cuisines": len(self.cuisines),
            "top_10_ingredients": ingredient_frequencies[:10],
            "top_5_cuisines": cuisine_counts.most_common(5),
            "avg_ingredients_per_recipe": np.mean(ingredient_counts),
            "min_ingredients": min(ingredient_counts),
            "max_ingredients": max(ingredient_counts),
            "median_ingredients": np.median(ingredient_counts)
        }