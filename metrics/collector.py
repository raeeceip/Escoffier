"""
Metrics Collector for ChefBench
Collects, analyzes, and visualizes benchmark metrics
"""

import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# Set style for better-looking plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


class MetricsCollector:
    """Collect and analyze ChefBench evaluation metrics"""
    
    def __init__(self, output_dir: str = "results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.charts_dir = self.output_dir / "charts"
        self.charts_dir.mkdir(exist_ok=True)
        
        self.data_dir = self.output_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Storage for metrics
        self.scenario_results: List[Dict] = []
        self.agent_performances: Dict[str, List[Dict]] = defaultdict(list)
        self.model_comparisons: Dict[str, Dict] = {}
        
    def record_scenario(
        self, 
        scenario_name: str,
        coordinator_metrics: Dict[str, Any],
        scenario_config: Dict[str, Any]
    ):
        """Record results from a scenario execution"""
        timestamp = datetime.now().isoformat()
        
        result = {
            "timestamp": timestamp,
            "scenario_name": scenario_name,
            "config": scenario_config,
            "metrics": coordinator_metrics,
            "duration": coordinator_metrics.get("duration", 0)
        }
        
        self.scenario_results.append(result)
        
        # Extract agent-specific metrics
        if "agent_metrics" in coordinator_metrics:
            for agent_name, agent_data in coordinator_metrics["agent_metrics"].get("agents", {}).items():
                self.agent_performances[agent_name].append({
                    "timestamp": timestamp,
                    "scenario": scenario_name,
                    **agent_data
                })
        
        # Save to file
        self._save_scenario_result(result)
        
        logger.info(f"Recorded scenario: {scenario_name}")
    
    def _save_scenario_result(self, result: Dict):
        """Save individual scenario result to JSON"""
        timestamp = result["timestamp"].replace(":", "-").replace(".", "-")
        filename = f"{result['scenario_name']}_{timestamp}.json"
        filepath = self.data_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2, default=str)
    
    def analyze_model_comparison(
        self, 
        model_groups: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Compare performance across different models"""
        comparison = {}
        
        for model_name, agent_names in model_groups.items():
            agent_metrics = []
            
            for agent_name in agent_names:
                if agent_name in self.agent_performances:
                    agent_metrics.extend(self.agent_performances[agent_name])
            
            if agent_metrics:
                df = pd.DataFrame(agent_metrics)
                
                comparison[model_name] = {
                    "avg_success_rate": df["success_rate"].mean(),
                    "avg_quality": df["avg_quality"].mean(),
                    "avg_reasoning_time": df["avg_reasoning_time"].mean(),
                    "avg_collaboration_score": df["collaboration_score"].mean(),
                    "avg_authority_compliance": df["authority_compliance"].mean(),
                    "total_tasks": df["tasks_completed"].sum(),
                    "agent_count": len(agent_names),
                    "scenario_count": len(df["scenario"].unique())
                }
        
        self.model_comparisons = comparison
        return comparison
    
    def generate_charts(self) -> List[Path]:
        """Generate comprehensive visualization charts"""
        generated_files = []
        
        # 1. Model Comparison Bar Chart
        if self.model_comparisons:
            fig, axes = plt.subplots(2, 3, figsize=(15, 10))
            fig.suptitle("Model Performance Comparison", fontsize=16, fontweight='bold')
            
            metrics = [
                ("avg_success_rate", "Success Rate"),
                ("avg_quality", "Quality Score"),
                ("avg_reasoning_time", "Reasoning Time (s)"),
                ("avg_collaboration_score", "Collaboration Score"),
                ("avg_authority_compliance", "Authority Compliance"),
                ("total_tasks", "Total Tasks Completed")
            ]
            
            for idx, (metric_key, metric_name) in enumerate(metrics):
                ax = axes[idx // 3, idx % 3]
                
                models = list(self.model_comparisons.keys())
                values = [self.model_comparisons[m].get(metric_key, 0) for m in models]
                
                bars = ax.bar(models, values)
                ax.set_title(metric_name)
                ax.set_xlabel("Model")
                ax.set_ylabel(metric_name)
                ax.tick_params(axis='x', rotation=45)
                
                # Color bars by performance
                colors = ['red' if v < np.mean(values) else 'green' for v in values]
                for bar, color in zip(bars, colors):
                    bar.set_color(color)
                    bar.set_alpha(0.7)
            
            plt.tight_layout()
            filepath = self.charts_dir / "model_comparison.png"
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            generated_files.append(filepath)
            logger.info(f"Generated model comparison chart: {filepath}")
        
        # 2. Agent Role Performance Heatmap
        if self.agent_performances:
            role_metrics = defaultdict(list)
            
            for agent_name, performances in self.agent_performances.items():
                for perf in performances:
                    role = perf.get("role", "unknown")
                    role_metrics[role].append({
                        "success_rate": perf.get("success_rate", 0),
                        "quality": perf.get("avg_quality", 0),
                        "collaboration": perf.get("collaboration_score", 0),
                        "authority": perf.get("authority_compliance", 0)
                    })
            
            # Create heatmap data
            roles = list(role_metrics.keys())
            metrics = ["success_rate", "quality", "collaboration", "authority"]
            
            heatmap_data = []
            for role in roles:
                role_data = role_metrics[role]
                if role_data:
                    df = pd.DataFrame(role_data)
                    heatmap_data.append(df[metrics].mean().values)
                else:
                    heatmap_data.append([0] * len(metrics))
            
            heatmap_array = np.array(heatmap_data)
            
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(
                heatmap_array,
                xticklabels=metrics,
                yticklabels=roles,
                annot=True,
                fmt='.2f',
                cmap='RdYlGn',
                vmin=0,
                vmax=1,
                ax=ax
            )
            ax.set_title("Agent Role Performance Heatmap", fontsize=14, fontweight='bold')
            ax.set_xlabel("Metrics")
            ax.set_ylabel("Agent Roles")
            
            plt.tight_layout()
            filepath = self.charts_dir / "role_performance_heatmap.png"
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            generated_files.append(filepath)
            logger.info(f"Generated role performance heatmap: {filepath}")
        
        # 3. Time Series Performance
        if self.scenario_results and len(self.scenario_results) > 1:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle("Performance Over Time", fontsize=16, fontweight='bold')
            
            # Extract time series data
            timestamps = []
            success_rates = []
            quality_scores = []
            collaboration_scores = []
            hierarchy_compliance = []
            
            for result in self.scenario_results:
                team_metrics = result["metrics"].get("agent_metrics", {}).get("team", {})
                timestamps.append(result["timestamp"])
                success_rates.append(team_metrics.get("overall_success_rate", 0))
                quality_scores.append(team_metrics.get("average_quality", 0))
                collaboration_scores.append(team_metrics.get("unique_collaborations", 0))
                hierarchy_compliance.append(team_metrics.get("hierarchy_compliance", 0))
            
            # Convert timestamps to sequential indices for plotting
            x_indices = range(len(timestamps))
            
            # Plot each metric
            axes[0, 0].plot(x_indices, success_rates, marker='o', linewidth=2)
            axes[0, 0].set_title("Success Rate")
            axes[0, 0].set_xlabel("Scenario")
            axes[0, 0].set_ylabel("Rate")
            axes[0, 0].set_ylim([0, 1])
            axes[0, 0].grid(True, alpha=0.3)
            
            axes[0, 1].plot(x_indices, quality_scores, marker='s', linewidth=2, color='orange')
            axes[0, 1].set_title("Average Quality")
            axes[0, 1].set_xlabel("Scenario")
            axes[0, 1].set_ylabel("Score")
            axes[0, 1].set_ylim([0, 1])
            axes[0, 1].grid(True, alpha=0.3)
            
            axes[1, 0].plot(x_indices, collaboration_scores, marker='^', linewidth=2, color='green')
            axes[1, 0].set_title("Collaboration Count")
            axes[1, 0].set_xlabel("Scenario")
            axes[1, 0].set_ylabel("Count")
            axes[1, 0].grid(True, alpha=0.3)
            
            axes[1, 1].plot(x_indices, hierarchy_compliance, marker='d', linewidth=2, color='red')
            axes[1, 1].set_title("Hierarchy Compliance")
            axes[1, 1].set_xlabel("Scenario")
            axes[1, 1].set_ylabel("Score")
            axes[1, 1].set_ylim([0, 1])
            axes[1, 1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            filepath = self.charts_dir / "performance_timeline.png"
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            generated_files.append(filepath)
            logger.info(f"Generated performance timeline: {filepath}")
        
        # 4. Communication Pattern Analysis
        if self.scenario_results:
            fig, axes = plt.subplots(1, 2, figsize=(15, 6))
            fig.suptitle("Communication Patterns", fontsize=16, fontweight='bold')
            
            # Aggregate communication by role
            role_messages = defaultdict(int)
            total_messages_per_scenario = []
            
            for result in self.scenario_results:
                team_metrics = result["metrics"].get("agent_metrics", {}).get("team", {})
                comm_by_role = team_metrics.get("communication_by_role", {})
                
                for role, count in comm_by_role.items():
                    role_messages[role] += count
                
                total_messages_per_scenario.append(team_metrics.get("total_messages", 0))
            
            # Pie chart of messages by role
            if role_messages:
                roles = list(role_messages.keys())
                counts = list(role_messages.values())
                
                axes[0].pie(counts, labels=roles, autopct='%1.1f%%', startangle=90)
                axes[0].set_title("Messages by Role")
            
            # Bar chart of messages per scenario
            if total_messages_per_scenario:
                scenario_names = [r["scenario_name"] for r in self.scenario_results]
                axes[1].bar(range(len(scenario_names)), total_messages_per_scenario)
                axes[1].set_xlabel("Scenario Index")
                axes[1].set_ylabel("Total Messages")
                axes[1].set_title("Message Volume per Scenario")
                axes[1].tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            filepath = self.charts_dir / "communication_patterns.png"
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            generated_files.append(filepath)
            logger.info(f"Generated communication patterns chart: {filepath}")
        
        return generated_files
    
    def generate_report(self) -> Path:
        """Generate comprehensive text report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"benchmark_report_{timestamp}.md"
        
        with open(report_file, 'w') as f:
            f.write("# ChefBench Evaluation Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Summary Statistics
            f.write("## Summary Statistics\n\n")
            f.write(f"- Total Scenarios Run: {len(self.scenario_results)}\n")
            f.write(f"- Unique Agents Tested: {len(self.agent_performances)}\n")
            f.write(f"- Models Compared: {len(self.model_comparisons)}\n\n")
            
            # Model Comparison
            if self.model_comparisons:
                f.write("## Model Performance Comparison\n\n")
                f.write("| Model | Success Rate | Quality | Reasoning Time | Collaboration | Authority |\n")
                f.write("|-------|-------------|---------|----------------|---------------|----------|\n")
                
                for model, metrics in self.model_comparisons.items():
                    f.write(f"| {model} | "
                           f"{metrics['avg_success_rate']:.3f} | "
                           f"{metrics['avg_quality']:.3f} | "
                           f"{metrics['avg_reasoning_time']:.3f}s | "
                           f"{metrics['avg_collaboration_score']:.3f} | "
                           f"{metrics['avg_authority_compliance']:.3f} |\n")
                f.write("\n")
            
            # Scenario Details
            f.write("## Scenario Execution Details\n\n")
            for result in self.scenario_results[-5:]:  # Last 5 scenarios
                f.write(f"### {result['scenario_name']}\n")
                f.write(f"- Timestamp: {result['timestamp']}\n")
                f.write(f"- Duration: {result['duration']:.2f}s\n")
                
                team_metrics = result["metrics"].get("agent_metrics", {}).get("team", {})
                f.write(f"- Success Rate: {team_metrics.get('overall_success_rate', 0):.3f}\n")
                f.write(f"- Average Quality: {team_metrics.get('average_quality', 0):.3f}\n")
                f.write(f"- Total Messages: {team_metrics.get('total_messages', 0)}\n")
                f.write(f"- Unique Collaborations: {team_metrics.get('unique_collaborations', 0)}\n\n")
            
            # Key Findings
            f.write("## Key Findings\n\n")
            
            if self.model_comparisons:
                # Find best performing model
                best_model = max(
                    self.model_comparisons.items(),
                    key=lambda x: x[1]['avg_success_rate']
                )[0]
                f.write(f"- **Best Performing Model**: {best_model}\n")
                
                # Find most collaborative model
                most_collab = max(
                    self.model_comparisons.items(),
                    key=lambda x: x[1]['avg_collaboration_score']
                )[0]
                f.write(f"- **Most Collaborative Model**: {most_collab}\n")
                
                # Find fastest model
                fastest = min(
                    self.model_comparisons.items(),
                    key=lambda x: x[1]['avg_reasoning_time']
                )[0]
                f.write(f"- **Fastest Reasoning Model**: {fastest}\n\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            f.write("Based on the evaluation results:\n\n")
            
            if self.model_comparisons:
                for model, metrics in self.model_comparisons.items():
                    if metrics['avg_success_rate'] < 0.5:
                        f.write(f"- {model} shows low success rate ({metrics['avg_success_rate']:.3f}), "
                               f"consider fine-tuning or using a different model\n")
                    if metrics['avg_authority_compliance'] < 0.7:
                        f.write(f"- {model} has poor authority compliance ({metrics['avg_authority_compliance']:.3f}), "
                               f"may need stronger hierarchical prompting\n")
            
            f.write("\n---\n")
            f.write("*ChefBench: Multi-Agent LLM Coordination Benchmark*\n")
        
        logger.info(f"Generated report: {report_file}")
        return report_file
    
    def export_to_csv(self) -> List[Path]:
        """Export all metrics to CSV files"""
        exported_files = []
        
        # Export scenario results
        if self.scenario_results:
            df_scenarios = pd.DataFrame(self.scenario_results)
            filepath = self.data_dir / f"scenarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df_scenarios.to_csv(filepath, index=False)
            exported_files.append(filepath)
        
        # Export agent performances
        if self.agent_performances:
            all_agent_data = []
            for agent_name, performances in self.agent_performances.items():
                for perf in performances:
                    perf['agent_name'] = agent_name
                    all_agent_data.append(perf)
            
            df_agents = pd.DataFrame(all_agent_data)
            filepath = self.data_dir / f"agent_performances_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df_agents.to_csv(filepath, index=False)
            exported_files.append(filepath)
        
        # Export model comparisons
        if self.model_comparisons:
            df_models = pd.DataFrame(self.model_comparisons).T
            filepath = self.data_dir / f"model_comparisons_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df_models.to_csv(filepath)
            exported_files.append(filepath)
        
        logger.info(f"Exported {len(exported_files)} CSV files")
        return exported_files