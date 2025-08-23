"""
Command Line Interface using Fire - Research and development workflows
"""
import fire
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any, cast
import json
import pandas as pd
from datetime import datetime
import uvicorn

from config import Config
from database import DatabaseManager
from agents.manager import AgentManager
from kitchen.engine import KitchenEngine
from recipes.manager import RecipeManager
from recipes.kaggle_parser import KaggleRecipeParser
from scenarios.executor import ScenarioExecutor, ScenarioConfig
from metrics.collector import MetricsCollector
from api.server import EscoffierAPI
from escoffier_types import AgentType, ScenarioType, TaskType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EscoffierCLI:
    """Command-line interface for Escoffier kitchen simulation"""
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        """Initialize CLI with configuration"""
        self.config_path = Path(config_path)
        
        # Initialize everything immediately - no reason to delay
        from config import get_settings
        from database import init_database, get_database
        from agents.manager import AgentManager
        from kitchen.engine import KitchenEngine
        from recipes.manager import RecipeManager
        from scenarios.executor import ScenarioExecutor
        from metrics.collector import MetricsCollector
        
        # Load configuration
        from config import load_settings
        self.config: Config = load_settings(self.config_path)
        
        # Initialize database
        self.db_manager: DatabaseManager = init_database(self.config, create_tables=True)
        
        # Initialize kitchen engine
        self.kitchen_engine: KitchenEngine = KitchenEngine(database=get_database(), settings=self.config)
        
        # Initialize components
        self.agent_manager: AgentManager = AgentManager(self.config, self.db_manager, self.kitchen_engine)
        self.recipe_manager: RecipeManager = RecipeManager(self.config, self.db_manager)
        self.scenario_executor: ScenarioExecutor = ScenarioExecutor(self.config, self.db_manager, self.agent_manager, self.kitchen_engine, self.recipe_manager)
        self.metrics_collector: MetricsCollector = MetricsCollector(self.config, self.db_manager)
        
        # Flag to track if async initialization is complete
        self.async_initialized = False
        
    async def _ensure_async_initialized(self):
        """Ensure async components are initialized"""
        if self.async_initialized:
            return
            
        logger.info("Completing async initialization...")
        
        # Only async initialization needed
        await self.agent_manager.initialize()
        
        self.async_initialized = True
        logger.info("Async initialization complete")
        
    def _run_async(self, coro):
        """Run async function in sync context"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            
    # Agent management commands
    def create_agent(
        self,
        name: str,
        agent_type: str,
        skills: str = "",
        llm_provider: str = "openai"
    ) -> str:
        """Create a new agent
        
        Args:
            name: Agent name
            agent_type: Type of agent (head_chef, sous_chef, line_cook, prep_cook)
            skills: Comma-separated list of skills
            llm_provider: LLM provider to use (openai, anthropic, cohere, huggingface)
        """
        async def _create():
            await self._ensure_async_initialized()
            
            # Parse agent type
            agent_type_enum = AgentType(agent_type.lower())
            
            # Handle skills parameter (could be string or tuple from Fire)
            if isinstance(skills, (list, tuple)):
                skills_list = list(skills)
            elif isinstance(skills, str):
                skills_list = [s.strip() for s in skills.split(",")] if skills else []
            else:
                skills_list = []
            
            agent_id = await self.agent_manager.create_agent(
                name=name,
                agent_type=agent_type_enum,
                skills=skills_list,
                llm_provider=llm_provider
            )
            
            print(f"Created agent: {name} (ID: {agent_id})")
            return agent_id
            
        return self._run_async(_create())
        
    def list_agents(self) -> None:
        """List all agents"""
        async def _list():
            
            # Query agents directly from database
            with self.db_manager.get_session() as session:
                from database.models import Agent
                agents = session.query(Agent).all()
                
                if not agents:
                    print("No agents found")
                    return
                    
                print(f"\n{'ID':<5} {'Name':<20} {'Role':<15} {'Provider':<12} {'Model':<15} {'Experience'}")
                print("-" * 85)
                
                for agent in agents:
                    print(f"{agent.id:<5} {agent.name:<20} {agent.role.value:<15} {agent.model_provider:<12} {agent.model_name:<15} {agent.experience_level}")
                
        return self._run_async(_list())
    
    def get_team_status(self) -> None:
        """Get current team status"""
        async def _status():
            await self._ensure_async_initialized()
            
            status = self.agent_manager.get_team_status()
            
            print("\n=== Team Status ===")
            print(f"Total agents: {status['total_agents']}")
            print(f"Average performance: {status['average_performance']:.2f}")
            print(f"Average stress: {status['average_stress']:.2f}")
            print(f"Average energy: {status['average_energy']:.2f}")
            print(f"Active collaborations: {status['active_collaborations']}")
            
            print("\nAgents by status:")
            for status_name, count in status['agents_by_status'].items():
                print(f"  {status_name}: {count}")
                
            print("\nAgents by type:")
            for type_name, count in status['agents_by_type'].items():
                print(f"  {type_name}: {count}")
                
        self._run_async(_status())
        
    # Recipe management commands
    def search_recipes(
        self,
        query: str = "",
        cuisine: str = "",
        difficulty: str = "",
        max_time: int = 0,
        ingredients: str = "",
        limit: int = 10
    ) -> None:
        """Search recipes with filters
        
        Args:
            query: Text search query
            cuisine: Cuisine filter
            difficulty: Difficulty filter (easy, medium, hard)
            max_time: Maximum total time in minutes
            ingredients: Comma-separated ingredients
            limit: Maximum number of results
        """
        async def _search():
            assert self.recipe_manager is not None, "Recipe manager not initialized"
            
            # Parse ingredients
            ingredients_list = [i.strip() for i in ingredients.split(",")] if ingredients else []
            
            results = self.recipe_manager.search_recipes(
                query=query,
                cuisine=cuisine,
                difficulty=difficulty,
                max_time=max_time if max_time and max_time > 0 else None,
                ingredients=ingredients_list
            )
            
            if results.empty:
                print("No recipes found matching criteria")
                return
                
            print(f"\n=== Found {len(results)} recipes ===")
            print(f"{'Name':<30} {'Cuisine':<12} {'Difficulty':<10} {'Time':<8} {'Servings'}")
            print("-" * 70)
            
            for i, (_, recipe) in enumerate(results.head(limit).iterrows()):
                total_time = recipe.get('prep_time', 0) + recipe.get('cook_time', 0)
                print(f"{recipe['name'][:29]:<30} {recipe['cuisine']:<12} "
                      f"{recipe['difficulty']:<10} {total_time:<8.0f} {recipe['servings']}")
                      
        self._run_async(_search())
        
    def get_recipe_recommendations(
        self,
        agent_skills: str = "",
        available_ingredients: str = "",
        time_limit: int = 60,
        difficulty: str = "medium",
        limit: int = 5
    ) -> None:
        """Get recipe recommendations based on constraints"""
        async def _recommend():
            
            skills_list = [s.strip() for s in agent_skills.split(",")] if agent_skills else []
            ingredients_list = [i.strip() for i in available_ingredients.split(",")] if available_ingredients else []
            
            recommendations = self.recipe_manager.get_recipe_recommendations(
                agent_skills=skills_list,
                available_ingredients=ingredients_list,
                time_limit=time_limit,
                difficulty_preference=difficulty
            )
            
            if not recommendations:
                print("No recipe recommendations found")
                return
                
            print(f"\n=== Top {min(limit, len(recommendations))} Recipe Recommendations ===")
            
            for i, rec in enumerate(recommendations[:limit]):
                print(f"\n{i+1}. {rec['name']} (Score: {rec['score']:.2f})")
                print(f"   Difficulty: {rec['difficulty']}, Time: {rec['total_time']} min")
                print(f"   Cuisine: {rec['cuisine']}")
                
                if rec['techniques_required']:
                    print(f"   Techniques: {', '.join(rec['techniques_required'])}")
                    
                if rec['missing_ingredients']:
                    print(f"   Missing ingredients: {', '.join(rec['missing_ingredients'])}")
                    
        self._run_async(_recommend())
        
    def recipe_stats(self) -> None:
        """Show recipe database statistics"""
        async def _stats():
            
            stats = self.recipe_manager.get_recipe_statistics()
            
            print("\n=== Recipe Database Statistics ===")
            print(f"Total recipes: {stats.get('total_recipes', 0)}")
            print(f"Average prep time: {stats.get('average_prep_time', 0):.1f} minutes")
            print(f"Average cook time: {stats.get('average_cook_time', 0):.1f} minutes")
            print(f"Average total time: {stats.get('average_total_time', 0):.1f} minutes")
            print(f"Average servings: {stats.get('average_servings', 0):.1f}")
            
            print("\nCuisines:")
            for cuisine, count in stats.get('cuisines', {}).items():
                print(f"  {cuisine}: {count}")
                
            print("\nDifficulty distribution:")
            for difficulty, count in stats.get('difficulty_distribution', {}).items():
                print(f"  {difficulty}: {count}")
                
            time_ranges = stats.get('time_ranges', {})
            print(f"\nTime ranges:")
            print(f"  Quick meals (≤30 min): {time_ranges.get('quick_meals', 0)}")
            print(f"  Medium meals (31-60 min): {time_ranges.get('medium_meals', 0)}")
            print(f"  Long meals (>60 min): {time_ranges.get('long_meals', 0)}")
            
        self._run_async(_stats())
        
    # Scenario execution commands
    def run_scenario(
        self,
        scenario_type: str,
        name: str = "",
        duration: int = 60,
        max_agents: int = 4,
        recipes: str = "",
        difficulty: str = "medium",
        time_pressure: float = 1.0,
        crisis_probability: float = 0.1
    ) -> str:
        """Execute a scenario
        
        Args:
            scenario_type: Type of scenario (cooking_challenge, service_rush, etc.)
            name: Scenario name (optional)
            duration: Duration in minutes
            max_agents: Maximum number of agents
            recipes: Comma-separated recipe IDs
            difficulty: Difficulty level
            time_pressure: Time pressure multiplier
            crisis_probability: Crisis event probability
        """
        async def _run():
            await self._ensure_async_initialized()
            
            # Parse recipe IDs
            if isinstance(recipes, int):
                # If recipes is a number, get that many recipe recommendations
                recipe_count = recipes
                recipe_ids = []
            elif isinstance(recipes, str) and recipes:
                # If recipes is a string, parse it as comma-separated IDs
                recipe_ids = [r.strip() for r in recipes.split(",")]
                recipe_count = len(recipe_ids)
            else:
                recipe_ids = []
                recipe_count = 0
            
            # If no recipes specified, add default recipes based on scenario type
            if not recipe_ids:
                if scenario_type.lower() == "collaboration_test":
                    recipe_ids = ["pasta_carbonara", "caesar_salad"]
                    recipe_count = len(recipe_ids)
                elif scenario_type.lower() == "service_rush":
                    recipe_ids = ["grilled_chicken", "roasted_vegetables", "caesar_salad"]
                    recipe_count = len(recipe_ids)
                elif scenario_type.lower() == "cooking_competition":
                    recipe_ids = ["beef_wellington", "chocolate_souffle", "lobster_bisque"]
                    recipe_count = len(recipe_ids)
                else:
                    recipe_ids = ["pasta_aglio_olio", "simple_salad"]
                    recipe_count = len(recipe_ids)
            
            # If still no recipes specified, get some recommendations
            if not recipe_ids and recipe_count > 0:
                recommendations = self.recipe_manager.get_recipe_recommendations(
                    agent_skills=[],
                    available_ingredients=[],
                    time_limit=duration,
                    difficulty_preference=difficulty
                )
                recipe_ids = [rec['recipe_id'] for rec in recommendations[:recipe_count]]
                
            scenario_id = f"scenario_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            config = ScenarioConfig(
                scenario_id=scenario_id,
                scenario_type=ScenarioType(scenario_type.lower()),
                duration_minutes=duration,
                max_agents=max_agents,
                recipes=recipe_ids,
                difficulty_level=difficulty,
                time_pressure=time_pressure,
                crisis_probability=crisis_probability
            )
            
            print(f"Starting scenario: {scenario_id}")
            print(f"Type: {scenario_type}, Duration: {duration} min, Agents: {max_agents}")
            print(f"Recipes: {len(recipe_ids)}, Difficulty: {difficulty}")
            
            result = await self.scenario_executor.execute_scenario(config)
            
            print(f"\n=== Scenario Complete ===")
            print(f"Status: {result.status}")
            print(f"Duration: {result.duration_seconds:.1f} seconds")
            print(f"Tasks completed: {result.tasks_completed}")
            print(f"Tasks failed: {result.tasks_failed}")
            print(f"Recipes completed: {result.recipes_completed}")
            print(f"Quality score: {result.quality_score:.2f}")
            print(f"Efficiency score: {result.efficiency_score:.2f}")
            print(f"Collaboration score: {result.collaboration_score:.2f}")
            
            if result.crisis_events:
                print(f"Crisis events: {len(result.crisis_events)}")
                
            return scenario_id
            
        return self._run_async(_run())
        
    def list_scenarios(self, limit: int = 10) -> None:
        """List recent scenarios"""
        async def _list():
            
            results = list(self.scenario_executor.execution_results.values())
            
            if not results:
                print("No scenarios found")
                return
                
            print(f"\n=== Recent Scenarios (showing {min(limit, len(results))}) ===")
            print(f"{'ID':<25} {'Status':<12} {'Duration':<10} {'Quality':<8} {'Efficiency'}")
            print("-" * 70)
            
            for result in results[-limit:]:
                print(f"{result.scenario_id[:24]:<25} {result.status:<12} "
                      f"{result.duration_seconds:<10.1f} {result.quality_score:<8.2f} "
                      f"{result.efficiency_score:.2f}")
                      
        self._run_async(_list())
    
    def list_options(self) -> None:
        """List all available scenario types, agent types, and difficulty levels"""
        from escoffier_types import ScenarioType, AgentType, DifficultyLevel, TaskType
        
        print("\n=== Available Scenario Types ===")
        for scenario_type in ScenarioType:
            print(f"  {scenario_type.value}")
            
        print("\n=== Available Agent Types ===")
        for agent_type in AgentType:
            print(f"  {agent_type.value}")
            
        print("\n=== Available Difficulty Levels ===")
        for difficulty in DifficultyLevel:
            print(f"  {difficulty.value}")
            
        print("\n=== Available Task Types ===")
        for task_type in TaskType:
            print(f"  {task_type.value}")
            
        print("\n=== Example Commands ===")
        print("  python -m cli.main run_scenario cooking_competition --duration=5 --max_agents=3")
        print("  python -m cli.main run_scenario service_rush --duration=10 --max_agents=4 --difficulty=hard")
        print("  python -m cli.main run_scenario collaboration_test --duration=3 --max_agents=2")
        
    # Metrics and analysis commands
    def metrics(self, export_csv: bool = False, generate_charts: bool = False, output_dir: str = "data/analytics") -> None:
        """Show system metrics with optional CSV export and chart generation
        
        Args:
            export_csv: Export metrics to CSV files
            generate_charts: Generate visualization charts
            output_dir: Directory for output files
        """
        async def _metrics():
            
            await self.metrics_collector.refresh_data()
            metrics = self.metrics_collector.calculate_all_metrics()
            
            print("\n=== System Metrics ===")
            for metric_name, value in metrics.items():
                print(f"{metric_name}: {value:.3f}")
            
            if export_csv or generate_charts:
                import os
                os.makedirs(output_dir, exist_ok=True)
                
                if export_csv:
                    # Export metrics data to CSV
                    csv_files = self.metrics_collector.export_to_csv(output_dir)
                    print(f"\n=== CSV Export Complete ===")
                    for file_path in csv_files:
                        print(f"Exported: {file_path}")
                
                if generate_charts:
                    # Generate visualization charts
                    chart_files = self.metrics_collector.generate_charts(output_dir)
                    print(f"\n=== Charts Generated ===")
                    for file_path in chart_files:
                        print(f"Generated: {file_path}")
                
        self._run_async(_metrics())
        
    def analyze_performance(self) -> None:
        """Analyze agent performance"""
        async def _analyze():
            
            analysis = self.metrics_collector.analyze_agent_performance()
            
            print("\n=== Agent Performance Analysis ===")
            print(f"Total agents: {analysis.get('total_agents', 0)}")
            
            print("\nTop performers:")
            for performer in analysis.get('top_performers', [])[:5]:
                print(f"  {performer['agent_name']}: {performer['score']:.2f} "
                      f"(success rate: {performer['success_rate']:.1%})")
                      
            print("\nNeed improvement:")
            for agent in analysis.get('improvement_needed', [])[:5]:
                print(f"  {agent['agent_name']}: {agent['score']:.2f} "
                      f"(success rate: {agent['success_rate']:.1%})")
                      
            print("\nPerformance by type:")
            for agent_type, perf in analysis.get('performance_by_type', {}).items():
                print(f"  {agent_type}: success rate {perf['success_rate']:.1%}, "
                      f"avg time {perf['avg_completion_time']:.1f} min")
                      
        self._run_async(_analyze())
        
    def analyze_collaboration(self) -> None:
        """Analyze collaboration patterns"""
        async def _analyze():
            
            analysis = self.metrics_collector.analyze_collaboration_patterns()
            
            print("\n=== Collaboration Analysis ===")
            print(f"Total communications: {analysis.get('total_communications', 0)}")
            
            print("\nMost communicative agents:")
            for agent in analysis.get('most_communicative_agents', [])[:5]:
                print(f"  {agent['agent_name']}: {agent['messages_sent']} messages")
                
            # Show communication frequency by hour
            freq = analysis.get('communication_frequency', {})
            if freq:
                print("\nCommunication frequency by hour:")
                for hour in sorted(freq.keys()):
                    print(f"  {hour:02d}:00 - {freq[hour]} messages")
                    
        self._run_async(_analyze())
        
    def generate_report(self, output_file: str = "") -> str:
        """Generate comprehensive analysis report"""
        async def _generate():
            
            report = self.metrics_collector.generate_comprehensive_report()
            
            if not output_file:
                output_path = f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            else:
                output_path = output_file
                
            # Save report
            with open(output_path, 'w') as f:
                json.dump(report.to_dict(), f, indent=2, default=str)
                
            print(f"\n=== Analysis Report Generated ===")
            print(f"Report ID: {report.report_id}")
            print(f"Generated at: {report.generated_at}")
            print(f"Saved to: {output_path}")
            
            print(f"\nSummary: {report.summary}")
            
            print(f"\nFindings ({len(report.findings)}):")
            for finding in report.findings:
                print(f"  [{finding['severity'].upper()}] {finding['title']}")
                print(f"    {finding['description']}")
                
            print(f"\nRecommendations ({len(report.recommendations)}):")
            for rec in report.recommendations:
                print(f"  [{rec['priority'].upper()}] {rec['title']}")
                print(f"    {rec['description']}")
                
            if report.visualizations:
                print(f"\nVisualizations generated: {len(report.visualizations)}")
                for viz in report.visualizations:
                    print(f"  {viz}")
                    
            return output_path
            
        return self._run_async(_generate())
        
    def export_data(self, format: str = "csv", output_dir: str = "exports") -> str:
        """Export all data for research"""
        async def _export():
            
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Export metrics data
            metrics_file = self.metrics_collector.export_metrics_data(
                format=format,
                output_path=str(output_path / f"metrics_{timestamp}")
            )
            
            # Export recipe data
            recipe_file = self.recipe_manager.export_recipe_data(
                format=format,
                output_path=str(output_path / f"recipes_{timestamp}")
            )
            
            print(f"\n=== Data Export Complete ===")
            print(f"Metrics: {metrics_file}")
            print(f"Recipes: {recipe_file}")
            print(f"Format: {format}")
            
            return str(output_path)
            
        return self._run_async(_export())
        
    # Server commands
    def serve(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        reload: bool = False,
        workers: int = 1
    ) -> None:
        """Start the FastAPI server
        
        Args:
            host: Host to bind to
            port: Port to bind to
            reload: Enable auto-reload for development
            workers: Number of worker processes
        """
        async def _init_api():
            api = EscoffierAPI(self.config)
            await api.initialize()
            return api
            
        # Initialize the API first
        api = self._run_async(_init_api())
        
        print(f"Starting Escoffier API server on {host}:{port}")
        print(f"Documentation will be available at http://{host}:{port}/docs")
        
        # Run the server
        uvicorn.run(
            api.app,
            host=host,
            port=port,
            reload=reload,
            workers=workers if not reload else 1,
            log_level="info"
        )
        
    # Utility commands
    def init_db(self) -> None:
        """Initialize database with sample data"""
        async def _init():
            
            # Create some sample agents
            agent_configs = [
                ("Gordon", "head_chef", "leadership,knife_skills,sauce_making", "openai"),
                ("Julia", "sous_chef", "baking,pastry,organization", "anthropic"),
                ("Marco", "line_cook", "grilling,sauteing,plating", "cohere"),
                ("Marie", "prep_cook", "knife_skills,vegetable_prep,inventory", "huggingface")
            ]
            
            print("Creating sample agents...")
            for name, agent_type, skills, provider in agent_configs:
                try:
                    agent_id = await self.agent_manager.create_agent(
                        name=name,
                        agent_type=AgentType(agent_type),
                        skills=skills.split(","),
                        llm_provider=provider
                    )
                    print(f"  Created {name} ({agent_type}): {agent_id}")
                except Exception as e:
                    print(f"  Failed to create {name}: {e}")
                    
            print("Database initialization complete")
            
        self._run_async(_init())
        
    def parse_kaggle_recipes(
        self,
        train_path: str,
        test_path: Optional[str] = None,
        output_dir: Optional[str] = None,
        use_multiprocessing: bool = True,
        export_to_manager: bool = True
    ) -> Dict[str, str]:
        """Parse Kaggle recipe dataset and convert to structured format
        
        Args:
            train_path: Path to training JSON file (required)
            test_path: Path to test JSON file (optional)
            output_dir: Output directory for processed files
            use_multiprocessing: Use multiprocessing for large datasets
            export_to_manager: Export to recipe manager for immediate use
        """
        async def _parse():
            
            print(f"🔍 Parsing Kaggle recipe dataset...")
            print(f"Training data: {train_path}")
            if test_path:
                print(f"Test data: {test_path}")
                
            parser = KaggleRecipeParser(self.config, self.db_manager)
            
            # Load dataset
            print("📂 Loading dataset...")
            recipe_count, ingredient_count = await parser.load_kaggle_dataset(
                train_path, test_path, use_multiprocessing
            )
            
            print(f"✅ Loaded {recipe_count:,} recipes with {ingredient_count:,} unique ingredients")
            
            # Convert to structured format
            print("🔄 Converting to structured format...")
            structured_df = parser.convert_to_structured_recipes()
            print(f"✅ Converted to {len(structured_df):,} structured recipes")
            
            # Save processed data
            print("💾 Saving processed data...")
            files_created = parser.save_processed_data(output_dir)
            print("📄 Created files:")
            for file_type, file_path in files_created.items():
                print(f"  • {file_type}: {file_path}")
                
            # Export to recipe manager if requested
            if export_to_manager and self.recipe_manager:
                print("📤 Exporting to recipe manager...")
                exported_count = await parser.export_to_recipe_manager(self.recipe_manager)
                print(f"✅ Exported {exported_count:,} recipes to recipe manager")
                
            # Show statistics
            print("\n📊 Dataset Statistics:")
            ingredient_stats = parser.get_ingredient_statistics()
            cuisine_stats = parser.get_cuisine_statistics()
            
            print(f"\n🥕 Top 10 Most Common Ingredients:")
            for i, (ingredient, count) in enumerate(ingredient_stats['most_common_ingredients'][:10], 1):
                percentage = (count / ingredient_stats['total_recipes']) * 100
                print(f"  {i:2d}. {ingredient:<20} {count:>6,} ({percentage:5.1f}%)")
                
            print(f"\n🍜 Top 10 Cuisines:")
            for i, (cuisine, count) in enumerate(cuisine_stats['most_popular_cuisines'][:10], 1):
                percentage = (count / cuisine_stats['total_recipes']) * 100
                print(f"  {i:2d}. {str(cuisine).title():<15} {count:>6,} ({percentage:5.1f}%)")
                
            print(f"\n📈 Processing Summary:")
            print(f"  • Total recipes: {recipe_count:,}")
            print(f"  • Unique ingredients: {ingredient_count:,}")
            print(f"  • Unique cuisines: {len(cuisine_stats['cuisine_distribution']):,}")
            print(f"  • Average ingredients per recipe: {ingredient_count / recipe_count:.1f}")
            
            return files_created
            
        return self._run_async(_parse())
        
    def download_kaggle_dataset(
        self,
        dataset: str = "kaggle/recipe-ingredients-dataset",
        output_dir: Optional[str] = None
    ) -> None:
        """Download Kaggle dataset (requires kaggle CLI)
        
        Args:
            dataset: Kaggle dataset identifier
            output_dir: Directory to download to
        """
        import subprocess
        import os
        
        if output_dir is None:
            output_dir = str(self.config.data_dir) if self.config else "data"
            
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        print(f"📥 Downloading Kaggle dataset: {dataset}")
        print(f"📁 Output directory: {output_path}")
        
        try:
            # Check if kaggle CLI is installed
            result = subprocess.run(
                ["kaggle", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✅ Kaggle CLI found: {result.stdout.strip()}")
            
            # Download dataset
            cmd = ["kaggle", "datasets", "download", "-d", dataset, "-p", str(output_path), "--unzip"]
            print(f"🔄 Running: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("✅ Download complete!")
            
            # List downloaded files
            downloaded_files = list(output_path.glob("*.json"))
            print(f"📄 Downloaded files:")
            for file_path in downloaded_files:
                size_mb = file_path.stat().st_size / (1024 * 1024)
                print(f"  • {file_path.name} ({size_mb:.1f} MB)")
                
            # Suggest next steps
            train_file = output_path / "train.json"
            test_file = output_path / "test.json"
            
            if train_file.exists():
                print(f"\n🚀 Next step: Parse the dataset with:")
                print(f"python -m cli.main parse_kaggle_recipes \"{train_file}\"", end="")
                if test_file.exists():
                    print(f" --test_path \"{test_file}\"")
                else:
                    print()
                    
        except subprocess.CalledProcessError as e:
            print(f"❌ Error downloading dataset: {e}")
            print(f"stderr: {e.stderr}")
            print("\n💡 Make sure you have:")
            print("  1. Installed kaggle CLI: pip install kaggle")
            print("  2. Configured API credentials: https://github.com/Kaggle/kaggle-api#api-credentials")
        except FileNotFoundError:
            print("❌ Kaggle CLI not found!")
            print("💡 Install with: pip install kaggle")
            print("💡 Configure credentials: https://github.com/Kaggle/kaggle-api#api-credentials")
            
    def analyze_recipe_dataset(self, dataset_path: Optional[str] = None) -> None:
        """Analyze loaded recipe dataset
        
        Args:
            dataset_path: Path to CSV file (optional, uses current recipe manager data if not provided)
        """
        async def _analyze():
            
            if dataset_path:
                print(f"📊 Analyzing recipe dataset: {dataset_path}")
                # Load specific dataset
                df = pd.read_csv(dataset_path)
            else:
                print("📊 Analyzing current recipe manager data")
                if not self.recipe_manager or self.recipe_manager.recipes_df is None or self.recipe_manager.recipes_df.empty:
                    print("❌ No recipe data loaded. Load recipes first or specify dataset_path")
                    return
                df = self.recipe_manager.recipes_df
                
            print(f"📋 Dataset Overview:")
            print(f"  • Total recipes: {len(df):,}")
            print(f"  • Columns: {', '.join(df.columns)}")
            
            # Basic statistics
            if 'cuisine' in df.columns:
                cuisine_counts = df['cuisine'].value_counts()
                print(f"\n🍜 Cuisine Distribution:")
                for cuisine, count in cuisine_counts.head(10).items():
                    percentage = (count / len(df)) * 100
                    print(f"  • {str(cuisine).title():<15} {count:>6,} ({percentage:5.1f}%)")
                    
            if 'difficulty' in df.columns:
                difficulty_counts = df['difficulty'].value_counts()
                print(f"\n⚡ Difficulty Distribution:")
                for difficulty, count in difficulty_counts.items():
                    percentage = (count / len(df)) * 100
                    print(f"  • {str(difficulty).title():<10} {count:>6,} ({percentage:5.1f}%)")
                    
            if 'prep_time' in df.columns and 'cook_time' in df.columns:
                df['total_time'] = df['prep_time'] + df['cook_time']
                print(f"\n⏱️  Time Statistics:")
                print(f"  • Avg prep time: {df['prep_time'].mean():.1f} min")
                print(f"  • Avg cook time: {df['cook_time'].mean():.1f} min")
                print(f"  • Avg total time: {df['total_time'].mean():.1f} min")
                print(f"  • Quick recipes (<30 min): {len(df[df['total_time'] <= 30]):,}")
                print(f"  • Long recipes (>2 hours): {len(df[df['total_time'] > 120]):,}")
                
            if 'ingredient_count' in df.columns:
                print(f"\n🥕 Ingredient Statistics:")
                print(f"  • Avg ingredients per recipe: {df['ingredient_count'].mean():.1f}")
                print(f"  • Min ingredients: {df['ingredient_count'].min()}")
                print(f"  • Max ingredients: {df['ingredient_count'].max()}")
                print(f"  • Simple recipes (≤5 ingredients): {len(df[df['ingredient_count'] <= 5]):,}")
                print(f"  • Complex recipes (>15 ingredients): {len(df[df['ingredient_count'] > 15]):,}")
                
            # Recipe manager specific analysis
            if not dataset_path and self.recipe_manager:
                stats = self.recipe_manager.get_recipe_statistics()
                if stats:
                    print(f"\n📈 Recipe Manager Statistics:")
                    print(f"  • Total recipes loaded: {stats['total_recipes']:,}")
                    if 'nutrition_stats' in stats:
                        nutrition = stats['nutrition_stats']
                        print(f"  • Avg calories per serving: {nutrition['average_calories']:.0f}")
                        print(f"  • Avg protein per serving: {nutrition['average_protein']:.1f}g")
                        
        self._run_async(_analyze())

    def cleanup(self) -> None:
        """Cleanup resources and reset system"""
        async def _cleanup():
            if True:  # Always do cleanup since we initialize immediately
                if self.agent_manager:
                    await self.agent_manager.cleanup()
                if self.scenario_executor:
                    await self.scenario_executor.cleanup()
                if self.db_manager and hasattr(self.db_manager, 'close'):
                    self.db_manager.close()  # Remove await since close() isn't async
                    
            print("Cleanup complete")
            
        self._run_async(_cleanup())
        
    def version(self) -> None:
        """Show version information"""
        print("Escoffier Kitchen Simulation Platform")
        print("Version: 1.0.0")
        print("Python Implementation with Multi-Agent LLM Integration")
        print("Research Platform for Computational Cooking and Collaboration")


def main():
    """Main CLI entry point"""
    # Handle the case where no config is provided
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1].endswith('.yaml'):
        config_path = sys.argv[1]
        sys.argv = [sys.argv[0]] + sys.argv[2:]  # Remove config from args
    else:
        config_path = "configs/config.yaml"
        
    cli = EscoffierCLI(config_path)
    
    try:
        fire.Fire(cli)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        cli.cleanup()
    except Exception as e:
        print(f"Error: {e}")
        cli.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()