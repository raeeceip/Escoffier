"""
Command Line Interface using Fire - Research and development workflows
"""
import fire
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import pandas as pd
from datetime import datetime
import uvicorn

from config import Config
from database import DatabaseManager
from agents.manager import AgentManager
from kitchen.engine import KitchenEngine
from recipes.manager import RecipeManager
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
        self.config: Optional[Config] = None
        self.components_initialized = False
        
        # Components
        self.db_manager: Optional[DatabaseManager] = None
        self.agent_manager: Optional[AgentManager] = None
        self.kitchen_engine: Optional[KitchenEngine] = None
        self.recipe_manager: Optional[RecipeManager] = None
        self.scenario_executor: Optional[ScenarioExecutor] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        
    async def _ensure_initialized(self):
        """Ensure all components are initialized"""
        if self.components_initialized:
            return
            
        logger.info("Initializing Escoffier components...")
        
        # Load configuration
        from config import get_settings
        from database import init_database, get_database
        from agents.manager import AgentManager
        from kitchen.engine import KitchenEngine
        from recipes.manager import RecipeManager
        from scenarios.executor import ScenarioExecutor
        from metrics.collector import MetricsCollector
        
        self.config = get_settings()
        
        # Initialize database first
        self.db_manager = init_database(self.config, create_tables=True)
        
        # Initialize kitchen engine with database and settings
        self.kitchen_engine = KitchenEngine(database=get_database(), settings=self.config) 
        
        # Initialize agent manager with dependencies
        self.agent_manager = AgentManager(self.config, self.db_manager, self.kitchen_engine)
        await self.agent_manager.initialize()
        
        # Initialize other components
        self.recipe_manager = RecipeManager(self.config, self.db_manager)
        self.scenario_executor = ScenarioExecutor(self.config, self.db_manager, self.agent_manager, self.kitchen_engine, self.recipe_manager)
        self.metrics_collector = MetricsCollector(self.config, self.db_manager)
        
        self.components_initialized = True
        logger.info("Initialization complete")
        
        self.components_initialized = True
        logger.info("Initialization complete")
        
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
            await self._ensure_initialized()
            
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
            await self._ensure_initialized()
            
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
            await self._ensure_initialized()
            
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
            await self._ensure_initialized()
            
            # Parse ingredients
            ingredients_list = [i.strip() for i in ingredients.split(",")] if ingredients else []
            
            results = self.recipe_manager.search_recipes(
                query=query if query else None,
                cuisine=cuisine if cuisine else None,
                difficulty=difficulty if difficulty else None,
                max_time=max_time if max_time > 0 else None,
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
            await self._ensure_initialized()
            
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
            await self._ensure_initialized()
            
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
            await self._ensure_initialized()
            
            # Parse recipe IDs
            recipe_ids = [r.strip() for r in recipes.split(",")] if recipes else []
            
            # If no recipes specified, get some recommendations
            if not recipe_ids:
                recommendations = self.recipe_manager.get_recipe_recommendations(
                    agent_skills=[],
                    available_ingredients=[],
                    time_limit=duration,
                    difficulty_preference=difficulty
                )
                recipe_ids = [rec['recipe_id'] for rec in recommendations[:3]]  # Use top 3
                
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
            await self._ensure_initialized()
            
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
        
    # Metrics and analysis commands
    def metrics(self, export_csv: bool = False, generate_charts: bool = False, output_dir: str = "data/analytics") -> None:
        """Show system metrics with optional CSV export and chart generation
        
        Args:
            export_csv: Export metrics to CSV files
            generate_charts: Generate visualization charts
            output_dir: Directory for output files
        """
        async def _metrics():
            await self._ensure_initialized()
            
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
            await self._ensure_initialized()
            
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
            await self._ensure_initialized()
            
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
            await self._ensure_initialized()
            
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
            await self._ensure_initialized()
            
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
            await self._ensure_initialized()
            
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
        
    def cleanup(self) -> None:
        """Cleanup resources and reset system"""
        async def _cleanup():
            if self.components_initialized:
                if self.agent_manager:
                    await self.agent_manager.cleanup()
                if self.scenario_executor:
                    await self.scenario_executor.cleanup()
                if self.db_manager and hasattr(self.db_manager, 'close'):
                    await self.db_manager.close()
                    
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