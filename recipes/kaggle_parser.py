"""
Kaggle Recipe Dataset Parser - Process large recipe datasets from Kaggle
Specifically designed for: https://www.kaggle.com/datasets/kaggle/recipe-ingredients-dataset
"""
import json
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
import re
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

from config import Config
from database.models import Recipe, Ingredient
from database import DatabaseManager
from escoffier_types import DifficultyLevel, RecipeType, CuisineType
from recipes.manager import RecipeManager, RecipeIngredient, RecipeStep, NutritionInfo

logger = logging.getLogger(__name__)


@dataclass
class KaggleRecipe:
    """Kaggle recipe format"""
    id: int
    cuisine: str
    ingredients: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'cuisine': self.cuisine,
            'ingredients': self.ingredients
        }


class KaggleRecipeParser:
    """Parser for Kaggle recipe datasets (JSON format)"""
    
    def __init__(self, config: Config, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.recipes_data: List[KaggleRecipe] = []
        self.processed_recipes: Optional[pd.DataFrame] = None
        self.ingredient_frequency: Dict[str, int] = {}
        self.cuisine_mapping: Dict[str, str] = {}
        
        # Common ingredient mappings for standardization
        self.ingredient_standardization = {
            # Proteins
            'ground beef': 'beef',
            'chicken breast': 'chicken',
            'chicken thigh': 'chicken',
            'pork chop': 'pork',
            'salmon fillet': 'salmon',
            'shrimp': 'shrimp',
            'tofu': 'tofu',
            
            # Vegetables
            'yellow onion': 'onion',
            'red onion': 'onion',
            'white onion': 'onion',
            'green bell pepper': 'bell pepper',
            'red bell pepper': 'bell pepper',
            'roma tomato': 'tomato',
            'cherry tomato': 'tomato',
            
            # Herbs & Spices
            'fresh basil': 'basil',
            'dried basil': 'basil',
            'fresh cilantro': 'cilantro',
            'ground black pepper': 'black pepper',
            'kosher salt': 'salt',
            'sea salt': 'salt',
            
            # Pantry items
            'extra virgin olive oil': 'olive oil',
            'vegetable oil': 'oil',
            'canola oil': 'oil',
            'all-purpose flour': 'flour',
            'white rice': 'rice',
            'brown rice': 'rice',
        }
        
        # Difficulty estimation based on ingredient count and complexity
        self.difficulty_thresholds = {
            'easy': {'max_ingredients': 8, 'complex_techniques': 0},
            'medium': {'max_ingredients': 15, 'complex_techniques': 2},
            'hard': {'max_ingredients': float('inf'), 'complex_techniques': float('inf')}
        }
        
        # Complex techniques/ingredients that increase difficulty
        self.complex_indicators = {
            'techniques': {
                'tempering', 'clarifying', 'emulsify', 'reduce', 'confit',
                'sous vide', 'ferment', 'cure', 'smoke', 'braise'
            },
            'ingredients': {
                'wine', 'cognac', 'shallot', 'truffle', 'saffron', 'cardamom',
                'star anise', 'lemongrass', 'galangal', 'miso', 'dashi'
            }
        }
        
    async def load_kaggle_dataset(
        self, 
        train_path: str = None, 
        test_path: Optional[str] = None,
        use_multiprocessing: bool = True
    ) -> Tuple[int, int]:
        """Load Kaggle recipe dataset from JSON files"""
        
        if train_path is None:
            train_path = str(self.config.data_dir / "kaggle_recipes_train.json")
        if test_path is None:
            test_path = str(self.config.data_dir / "kaggle_recipes_test.json")
            
        logger.info(f"Loading Kaggle dataset from {train_path} and {test_path}")
        
        loaded_count = 0
        
        # Load training data (has cuisine labels)
        if Path(train_path).exists():
            train_count = await self._load_json_file(train_path, has_cuisine=True, use_multiprocessing=use_multiprocessing)
            loaded_count += train_count
            logger.info(f"Loaded {train_count} training recipes")
        else:
            logger.warning(f"Training file not found: {train_path}")
            
        # Load test data (no cuisine labels)
        if test_path and Path(test_path).exists():
            test_count = await self._load_json_file(test_path, has_cuisine=False, use_multiprocessing=use_multiprocessing)
            loaded_count += test_count
            logger.info(f"Loaded {test_count} test recipes")
        elif test_path:
            logger.warning(f"Test file not found: {test_path}")
            
        # Build frequency analysis
        await self._build_ingredient_frequency()
        await self._build_cuisine_mapping()
        
        logger.info(f"Total recipes loaded: {loaded_count}")
        return loaded_count, len(self.ingredient_frequency)
        
    async def _load_json_file(
        self, 
        file_path: str, 
        has_cuisine: bool = True,
        use_multiprocessing: bool = True
    ) -> int:
        """Load recipes from JSON file with optional multiprocessing"""
        
        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            logger.info(f"Processing {len(data)} recipes from {file_path}")
            
            if use_multiprocessing and len(data) > 1000:
                # Use multiprocessing for large datasets
                recipes = await self._process_recipes_parallel(data, has_cuisine)
            else:
                # Process sequentially for smaller datasets
                recipes = [self._parse_kaggle_recipe(item, has_cuisine) for item in data]
                recipes = [r for r in recipes if r is not None]
                
            self.recipes_data.extend(recipes)
            return len(recipes)
            
        except Exception as e:
            logger.error(f"Failed to load JSON file {file_path}: {e}")
            return 0
            
    async def _process_recipes_parallel(self, data: List[Dict], has_cuisine: bool) -> List[KaggleRecipe]:
        """Process recipes using multiprocessing for performance"""
        
        # Split data into chunks for parallel processing
        num_processes = min(mp.cpu_count(), 8)  # Limit to 8 processes
        chunk_size = len(data) // num_processes
        chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
        
        # Process chunks in parallel
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            tasks = [
                loop.run_in_executor(
                    executor, 
                    self._process_recipe_chunk, 
                    chunk, 
                    has_cuisine
                )
                for chunk in chunks
            ]
            
            results = await asyncio.gather(*tasks)
            
        # Flatten results
        recipes = []
        for chunk_result in results:
            recipes.extend(chunk_result)
            
        return recipes
        
    @staticmethod
    def _process_recipe_chunk(chunk: List[Dict], has_cuisine: bool) -> List[KaggleRecipe]:
        """Process a chunk of recipes (for multiprocessing)"""
        parser = KaggleRecipeParser.__new__(KaggleRecipeParser)  # Create instance without __init__
        recipes = []
        
        for item in chunk:
            recipe = parser._parse_kaggle_recipe(item, has_cuisine)
            if recipe:
                recipes.append(recipe)
                
        return recipes
        
    def _parse_kaggle_recipe(self, item: Dict, has_cuisine: bool = True) -> Optional[KaggleRecipe]:
        """Parse individual Kaggle recipe item"""
        try:
            recipe_id = item.get('id')
            ingredients = item.get('ingredients', [])
            cuisine = item.get('cuisine', 'unknown') if has_cuisine else 'unknown'
            
            if not recipe_id or not ingredients:
                return None
                
            # Clean and standardize ingredients
            cleaned_ingredients = self._clean_ingredients(ingredients)
            
            return KaggleRecipe(
                id=recipe_id,
                cuisine=cuisine.lower(),
                ingredients=cleaned_ingredients
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse recipe item: {e}")
            return None
            
    def _clean_ingredients(self, ingredients: List[str]) -> List[str]:
        """Clean and standardize ingredient names"""
        cleaned = []
        
        for ingredient in ingredients:
            if not ingredient or not isinstance(ingredient, str):
                continue
                
            # Basic cleaning
            clean_ingredient = ingredient.strip().lower()
            
            # Remove common prefixes/suffixes
            clean_ingredient = re.sub(r'^(fresh|dried|ground|chopped|minced|sliced)\s+', '', clean_ingredient)
            clean_ingredient = re.sub(r'\s+(fresh|dried|ground|chopped|minced|sliced)$', '', clean_ingredient)
            
            # Remove measurements and quantities
            clean_ingredient = re.sub(r'^\d+(\.\d+)?\s*(cups?|tablespoons?|teaspoons?|lbs?|ounces?|grams?|kg|ml|l|tbsp|tsp|oz|g)\s+', '', clean_ingredient)
            
            # Remove common descriptors
            clean_ingredient = re.sub(r'\b(and|or|plus|with|without)\b', '', clean_ingredient)
            clean_ingredient = re.sub(r'\s+', ' ', clean_ingredient).strip()
            
            # Apply standardization mapping
            if clean_ingredient in self.ingredient_standardization:
                clean_ingredient = self.ingredient_standardization[clean_ingredient]
                
            if clean_ingredient:
                cleaned.append(clean_ingredient)
                
        return cleaned
        
    async def _build_ingredient_frequency(self):
        """Build ingredient frequency analysis"""
        self.ingredient_frequency.clear()
        
        for recipe in self.recipes_data:
            for ingredient in recipe.ingredients:
                self.ingredient_frequency[ingredient] = self.ingredient_frequency.get(ingredient, 0) + 1
                
        logger.info(f"Built ingredient frequency for {len(self.ingredient_frequency)} unique ingredients")
        
    async def _build_cuisine_mapping(self):
        """Build cuisine type mapping and statistics"""
        cuisine_counts = {}
        
        for recipe in self.recipes_data:
            cuisine = recipe.cuisine
            cuisine_counts[cuisine] = cuisine_counts.get(cuisine, 0) + 1
            
        self.cuisine_mapping = cuisine_counts
        logger.info(f"Found {len(cuisine_counts)} unique cuisines: {sorted(cuisine_counts.keys())}")
        
    def convert_to_structured_recipes(
        self, 
        estimate_times: bool = True,
        generate_instructions: bool = True
    ) -> pd.DataFrame:
        """Convert Kaggle recipes to structured format"""
        
        structured_recipes = []
        
        for recipe in self.recipes_data:
            # Estimate recipe properties
            difficulty = self._estimate_difficulty(recipe)
            prep_time, cook_time = self._estimate_times(recipe) if estimate_times else (30, 30)
            servings = self._estimate_servings(recipe)
            
            # Generate basic instructions if requested
            instructions = self._generate_basic_instructions(recipe) if generate_instructions else []
            
            # Extract techniques and equipment
            techniques = self._extract_techniques_from_ingredients(recipe.ingredients)
            equipment = self._extract_equipment_from_ingredients(recipe.ingredients)
            
            structured_recipe = {
                'id': recipe.id,
                'name': self._generate_recipe_name(recipe),
                'cuisine': recipe.cuisine,
                'difficulty': difficulty,
                'prep_time': prep_time,
                'cook_time': cook_time,
                'servings': servings,
                'ingredients': self._format_ingredients_for_recipe_manager(recipe.ingredients),
                'instructions': instructions,
                'techniques': techniques,
                'equipment': equipment,
                'ingredient_count': len(recipe.ingredients),
                'complexity_score': self._calculate_complexity_score(recipe)
            }
            
            structured_recipes.append(structured_recipe)
            
        self.processed_recipes = pd.DataFrame(structured_recipes)
        logger.info(f"Converted {len(structured_recipes)} Kaggle recipes to structured format")
        
        return self.processed_recipes
        
    def _estimate_difficulty(self, recipe: KaggleRecipe) -> str:
        """Estimate recipe difficulty based on ingredients and complexity"""
        
        ingredient_count = len(recipe.ingredients)
        complex_count = sum(
            1 for ingredient in recipe.ingredients
            if any(complex_ing in ingredient for complex_ing in self.complex_indicators['ingredients'])
        )
        
        # Check against thresholds
        if (ingredient_count <= self.difficulty_thresholds['easy']['max_ingredients'] and 
            complex_count <= self.difficulty_thresholds['easy']['complex_techniques']):
            return 'easy'
        elif (ingredient_count <= self.difficulty_thresholds['medium']['max_ingredients'] and 
              complex_count <= self.difficulty_thresholds['medium']['complex_techniques']):
            return 'medium'
        else:
            return 'hard'
            
    def _estimate_times(self, recipe: KaggleRecipe) -> Tuple[int, int]:
        """Estimate prep and cook times based on ingredients and cuisine"""
        
        base_prep = 15
        base_cook = 30
        
        # Adjust based on ingredient count
        ingredient_factor = min(2.0, len(recipe.ingredients) / 10)
        prep_time = int(base_prep * ingredient_factor)
        
        # Adjust based on cuisine (some cuisines typically take longer)
        cuisine_multipliers = {
            'italian': 1.2,
            'french': 1.4,
            'indian': 1.3,
            'chinese': 1.1,
            'thai': 1.2,
            'japanese': 1.0,
            'mexican': 1.1,
            'greek': 1.2,
            'moroccan': 1.5,
            'korean': 1.3
        }
        
        cuisine_factor = cuisine_multipliers.get(recipe.cuisine, 1.0)
        cook_time = int(base_cook * cuisine_factor)
        
        # Adjust for complex ingredients
        if any(ing in ['wine', 'stock', 'broth'] for ing in recipe.ingredients):
            cook_time += 15
        if any(ing in ['rice', 'pasta', 'beans'] for ing in recipe.ingredients):
            cook_time += 10
            
        return prep_time, cook_time
        
    def _estimate_servings(self, recipe: KaggleRecipe) -> int:
        """Estimate number of servings based on ingredients"""
        
        # Base estimate
        base_servings = 4
        
        # Adjust based on protein indicators
        protein_ingredients = ['chicken', 'beef', 'pork', 'fish', 'tofu', 'eggs']
        protein_count = sum(1 for ing in recipe.ingredients if any(p in ing for p in protein_ingredients))
        
        if protein_count >= 2:
            return 6  # Multiple proteins suggest larger recipe
        elif protein_count == 0:
            return 2  # No protein might be a side dish or small recipe
            
        return base_servings
        
    def _generate_recipe_name(self, recipe: KaggleRecipe) -> str:
        """Generate a descriptive recipe name based on ingredients and cuisine"""
        
        # Key ingredients to highlight
        key_ingredients = []
        protein_found = False
        
        # Look for proteins first
        proteins = ['chicken', 'beef', 'pork', 'fish', 'salmon', 'shrimp', 'tofu', 'turkey']
        for ingredient in recipe.ingredients:
            for protein in proteins:
                if protein in ingredient and not protein_found:
                    key_ingredients.append(protein.title())
                    protein_found = True
                    break
                    
        # Add a few other interesting ingredients
        interesting = ['curry', 'coconut', 'lemon', 'garlic', 'ginger', 'basil', 'tomato']
        for ingredient in recipe.ingredients:
            if len(key_ingredients) >= 3:
                break
            for item in interesting:
                if item in ingredient and item.title() not in key_ingredients:
                    key_ingredients.append(item.title())
                    break
                    
        # Fallback to first few ingredients if nothing interesting found
        if not key_ingredients:
            key_ingredients = [ing.title() for ing in recipe.ingredients[:2]]
            
        # Construct name
        if len(key_ingredients) == 1:
            name = f"{recipe.cuisine.title()} {key_ingredients[0]}"
        else:
            name = f"{' and '.join(key_ingredients)} {recipe.cuisine.title()} Style"
            
        return name
        
    def _format_ingredients_for_recipe_manager(self, ingredients: List[str]) -> List[str]:
        """Format ingredients for recipe manager compatibility"""
        formatted = []
        
        for ingredient in ingredients:
            # Add basic quantity estimation
            formatted_ingredient = f"1 unit {ingredient}"
            formatted.append(formatted_ingredient)
            
        return formatted
        
    def _generate_basic_instructions(self, recipe: KaggleRecipe) -> List[str]:
        """Generate basic cooking instructions based on ingredients"""
        
        instructions = []
        
        # Prep instruction
        prep_ingredients = [ing for ing in recipe.ingredients if 'onion' in ing or 'garlic' in ing]
        if prep_ingredients:
            instructions.append(f"Prepare ingredients: chop {', '.join(prep_ingredients[:3])}")
            
        # Cooking method based on cuisine and ingredients
        if any('oil' in ing for ing in recipe.ingredients):
            instructions.append("Heat oil in a large pan over medium heat")
            
        # Protein cooking
        proteins = [ing for ing in recipe.ingredients if any(p in ing for p in ['chicken', 'beef', 'pork', 'fish'])]
        if proteins:
            instructions.append(f"Cook {proteins[0]} until done")
            
        # Vegetable addition
        vegetables = [ing for ing in recipe.ingredients if any(v in ing for v in ['onion', 'pepper', 'tomato', 'carrot'])]
        if vegetables:
            instructions.append(f"Add {', '.join(vegetables[:3])} and cook until tender")
            
        # Seasoning
        seasonings = [ing for ing in recipe.ingredients if any(s in ing for s in ['salt', 'pepper', 'spice', 'herb'])]
        if seasonings:
            instructions.append(f"Season with {', '.join(seasonings[:3])}")
            
        # Final instruction
        instructions.append("Serve hot and enjoy!")
        
        return instructions
        
    def _extract_techniques_from_ingredients(self, ingredients: List[str]) -> List[str]:
        """Extract likely cooking techniques from ingredients"""
        techniques = []
        
        # Map ingredients to likely techniques
        technique_mapping = {
            'oil': ['sauté', 'fry'],
            'butter': ['sauté', 'roast'],
            'stock': ['braise', 'simmer'],
            'wine': ['deglaze', 'braise'],
            'cream': ['reduce', 'simmer'],
            'flour': ['thicken', 'dredge'],
            'egg': ['whisk', 'scramble'],
            'pasta': ['boil'],
            'rice': ['steam', 'simmer']
        }
        
        for ingredient in ingredients:
            for key, techs in technique_mapping.items():
                if key in ingredient:
                    techniques.extend(techs)
                    
        return list(set(techniques))  # Remove duplicates
        
    def _extract_equipment_from_ingredients(self, ingredients: List[str]) -> List[str]:
        """Extract likely equipment needs from ingredients"""
        equipment = ['pan', 'knife', 'cutting board']  # Basic equipment
        
        # Add equipment based on ingredients
        if any('pasta' in ing for ing in ingredients):
            equipment.append('large pot')
        if any('rice' in ing for ing in ingredients):
            equipment.append('rice cooker')
        if any('oil' in ing for ing in ingredients):
            equipment.append('skillet')
            
        return list(set(equipment))
        
    def _calculate_complexity_score(self, recipe: KaggleRecipe) -> float:
        """Calculate numerical complexity score"""
        score = 0.0
        
        # Base score from ingredient count
        score += len(recipe.ingredients) * 0.1
        
        # Complexity from special ingredients
        complex_count = sum(
            1 for ingredient in recipe.ingredients
            if any(complex_ing in ingredient for complex_ing in self.complex_indicators['ingredients'])
        )
        score += complex_count * 0.5
        
        # Cuisine complexity factor
        cuisine_complexity = {
            'french': 1.5,
            'indian': 1.3,
            'thai': 1.3,
            'moroccan': 1.4,
            'japanese': 1.2,
            'chinese': 1.1,
            'italian': 1.0,
            'mexican': 1.0,
            'american': 0.8
        }
        score *= cuisine_complexity.get(recipe.cuisine, 1.0)
        
        return round(score, 2)
        
    def get_ingredient_statistics(self) -> Dict:
        """Get comprehensive ingredient statistics"""
        if not self.ingredient_frequency:
            return {}
            
        # Sort by frequency
        sorted_ingredients = sorted(
            self.ingredient_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        total_recipes = len(self.recipes_data)
        
        stats = {
            'total_unique_ingredients': len(self.ingredient_frequency),
            'total_recipes': total_recipes,
            'most_common_ingredients': sorted_ingredients[:20],
            'rare_ingredients': sorted_ingredients[-20:],
            'ingredient_frequency_distribution': {
                'very_common': len([item for item in sorted_ingredients if item[1] > total_recipes * 0.1]),
                'common': len([item for item in sorted_ingredients if total_recipes * 0.05 < item[1] <= total_recipes * 0.1]),
                'uncommon': len([item for item in sorted_ingredients if total_recipes * 0.01 < item[1] <= total_recipes * 0.05]),
                'rare': len([item for item in sorted_ingredients if item[1] <= total_recipes * 0.01])
            }
        }
        
        return stats
        
    def get_cuisine_statistics(self) -> Dict:
        """Get comprehensive cuisine statistics"""
        if not self.cuisine_mapping:
            return {}
            
        total_recipes = len(self.recipes_data)
        sorted_cuisines = sorted(self.cuisine_mapping.items(), key=lambda x: x[1], reverse=True)
        
        stats = {
            'total_cuisines': len(self.cuisine_mapping),
            'total_recipes': total_recipes,
            'cuisine_distribution': dict(sorted_cuisines),
            'most_popular_cuisines': sorted_cuisines[:10],
            'cuisine_percentages': {
                cuisine: round((count / total_recipes) * 100, 2)
                for cuisine, count in sorted_cuisines
            }
        }
        
        return stats
        
    async def export_to_recipe_manager(self, recipe_manager: RecipeManager) -> int:
        """Export processed recipes to recipe manager"""
        if self.processed_recipes is None:
            await self.convert_to_structured_recipes()
            
        # Convert DataFrame to CSV format that recipe manager can read
        export_path = self.config.data_dir / "kaggle_recipes_converted.csv"
        self.processed_recipes.to_csv(export_path, index=False)
        
        # Load into recipe manager
        await recipe_manager.load_recipes_from_csv(str(export_path))
        
        logger.info(f"Exported {len(self.processed_recipes)} recipes to recipe manager")
        return len(self.processed_recipes)
        
    def save_processed_data(self, output_dir: Optional[str] = None) -> Dict[str, str]:
        """Save all processed data to files"""
        if output_dir is None:
            output_dir = str(self.config.data_dir / "kaggle_processed")
            
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        files_created = {}
        
        # Save structured recipes
        if self.processed_recipes is not None:
            recipes_file = output_path / f"structured_recipes_{timestamp}.csv"
            self.processed_recipes.to_csv(recipes_file, index=False)
            files_created['recipes'] = str(recipes_file)
            
        # Save ingredient frequency
        if self.ingredient_frequency:
            ingredients_file = output_path / f"ingredient_frequency_{timestamp}.json"
            with open(ingredients_file, 'w') as f:
                json.dump(self.ingredient_frequency, f, indent=2)
            files_created['ingredients'] = str(ingredients_file)
            
        # Save cuisine mapping
        if self.cuisine_mapping:
            cuisine_file = output_path / f"cuisine_stats_{timestamp}.json"
            with open(cuisine_file, 'w') as f:
                json.dump(self.cuisine_mapping, f, indent=2)
            files_created['cuisines'] = str(cuisine_file)
            
        # Save statistics
        stats = {
            'ingredient_stats': self.get_ingredient_statistics(),
            'cuisine_stats': self.get_cuisine_statistics(),
            'processing_summary': {
                'total_recipes_processed': len(self.recipes_data),
                'unique_ingredients': len(self.ingredient_frequency),
                'unique_cuisines': len(self.cuisine_mapping),
                'timestamp': timestamp
            }
        }
        
        stats_file = output_path / f"processing_stats_{timestamp}.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        files_created['stats'] = str(stats_file)
        
        logger.info(f"Saved processed data to {output_dir}")
        return files_created


# CLI interface for Kaggle parser
async def parse_kaggle_dataset_cli(
    train_path: str,
    test_path: str = None,
    output_dir: str = None,
    use_multiprocessing: bool = True
):
    """CLI function to parse Kaggle dataset"""
    from config import config
    from database import DatabaseManager
    
    db_manager = DatabaseManager(config)
    await db_manager.initialize()
    
    parser = KaggleRecipeParser(config, db_manager)
    
    # Load dataset
    recipe_count, ingredient_count = await parser.load_kaggle_dataset(
        train_path, test_path, use_multiprocessing
    )
    
    print(f"Loaded {recipe_count} recipes with {ingredient_count} unique ingredients")
    
    # Convert to structured format
    structured_df = parser.convert_to_structured_recipes()
    print(f"Converted to {len(structured_df)} structured recipes")
    
    # Save processed data
    files_created = parser.save_processed_data(output_dir)
    print("Created files:")
    for file_type, file_path in files_created.items():
        print(f"  {file_type}: {file_path}")
        
    # Print statistics
    ingredient_stats = parser.get_ingredient_statistics()
    cuisine_stats = parser.get_cuisine_statistics()
    
    print(f"\nTop 10 ingredients:")
    for ingredient, count in ingredient_stats['most_common_ingredients'][:10]:
        print(f"  {ingredient}: {count}")
        
    print(f"\nTop 10 cuisines:")
    for cuisine, count in cuisine_stats['most_popular_cuisines'][:10]:
        print(f"  {cuisine}: {count}")
        
    await db_manager.close()
    return files_created


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Parse Kaggle recipe dataset")
    parser.add_argument("train_path", help="Path to training JSON file")
    parser.add_argument("--test_path", help="Path to test JSON file")
    parser.add_argument("--output_dir", help="Output directory for processed files")
    parser.add_argument("--no_multiprocessing", action="store_true", help="Disable multiprocessing")
    
    args = parser.parse_args()
    
    asyncio.run(
        parse_kaggle_dataset_cli(
            args.train_path,
            args.test_path,
            args.output_dir,
            not args.no_multiprocessing
        )
    )