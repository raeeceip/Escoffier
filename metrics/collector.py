"""
Metrics and Analytics System - Comprehensive data collection and analysis
"""
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
import uuid
from enum import Enum
import statistics
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import seaborn as sns
import matplotlib.pyplot as plt

from config import Config
from database.models import MetricsSnapshot, Agent, Task, AgentAction, Communication, Scenario
from database import DatabaseManager
from escoffier_types import AgentType, TaskType, ActionType, ScenarioType, ScenarioStatus

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics to collect"""
    PERFORMANCE = "performance"
    EFFICIENCY = "efficiency"
    COLLABORATION = "collaboration"
    QUALITY = "quality"
    TIMING = "timing"
    COMMUNICATION = "communication"
    STRESS = "stress"
    LEARNING = "learning"


class AggregationType(Enum):
    """Types of data aggregation"""
    MEAN = "mean"
    MEDIAN = "median"
    SUM = "sum"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    STD = "std"
    PERCENTILE_95 = "p95"
    PERCENTILE_99 = "p99"


@dataclass
class MetricDefinition:
    """Definition of a metric to collect"""
    name: str
    metric_type: MetricType
    description: str
    source_table: str
    source_field: str
    aggregation: AggregationType
    filters: Dict[str, Any] = field(default_factory=dict)
    time_window: Optional[int] = None  # Minutes
    
    
@dataclass
class AnalysisReport:
    """Analysis report with findings and recommendations"""
    report_id: str
    title: str
    generated_at: datetime
    summary: str
    findings: List[Dict]
    recommendations: List[Dict]
    visualizations: List[str] = field(default_factory=list)
    raw_data: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'report_id': self.report_id,
            'title': self.title,
            'generated_at': self.generated_at.isoformat(),
            'summary': self.summary,
            'findings': self.findings,
            'recommendations': self.recommendations,
            'visualizations': self.visualizations,
            'raw_data': self.raw_data
        }


class MetricsCollector:
    """Comprehensive metrics collection and analysis system"""
    
    def __init__(self, config: Config, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.metrics_df: Optional[pd.DataFrame] = None
        self.agents_df: Optional[pd.DataFrame] = None
        self.tasks_df: Optional[pd.DataFrame] = None
        self.actions_df: Optional[pd.DataFrame] = None
        self.communications_df: Optional[pd.DataFrame] = None
        self.scenarios_df: Optional[pd.DataFrame] = None
        
        # Output directories
        self.output_dir = Path(config.data_dir) / "analytics"
        self.output_dir.mkdir(exist_ok=True)
        
        self.charts_dir = self.output_dir / "charts"
        self.charts_dir.mkdir(exist_ok=True)
        
        self.reports_dir = self.output_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Metric definitions
        self.metric_definitions = self._initialize_metric_definitions()
        
        # Analysis cache
        self.analysis_cache: Dict[str, Any] = {}
        self.last_refresh = None
        
    def _initialize_metric_definitions(self) -> List[MetricDefinition]:
        """Initialize standard metric definitions"""
        return [
            # Performance metrics
            MetricDefinition(
                name="avg_task_completion_time",
                metric_type=MetricType.PERFORMANCE,
                description="Average time to complete tasks",
                source_table="tasks",
                source_field="completion_time",
                aggregation=AggregationType.MEAN
            ),
            MetricDefinition(
                name="task_success_rate",
                metric_type=MetricType.PERFORMANCE,
                description="Percentage of successfully completed tasks",
                source_table="tasks",
                source_field="status",
                aggregation=AggregationType.MEAN,
                filters={"status": "completed"}
            ),
            MetricDefinition(
                name="agent_efficiency_score",
                metric_type=MetricType.EFFICIENCY,
                description="Overall agent efficiency",
                source_table="agents",
                source_field="performance_score",
                aggregation=AggregationType.MEAN
            ),
            
            # Collaboration metrics
            MetricDefinition(
                name="communication_frequency",
                metric_type=MetricType.COLLABORATION,
                description="Average communications per hour",
                source_table="communications",
                source_field="sent_at",
                aggregation=AggregationType.COUNT,
                time_window=60
            ),
            MetricDefinition(
                name="collaboration_success_rate",
                metric_type=MetricType.COLLABORATION,
                description="Success rate of collaborative tasks",
                source_table="tasks",
                source_field="status",
                aggregation=AggregationType.MEAN,
                filters={"task_type": "collaborate"}
            ),
            
            # Quality metrics
            MetricDefinition(
                name="recipe_quality_score",
                metric_type=MetricType.QUALITY,
                description="Average quality score of completed recipes",
                source_table="scenarios",
                source_field="quality_score",
                aggregation=AggregationType.MEAN
            ),
            
            # Timing metrics
            MetricDefinition(
                name="scenario_duration",
                metric_type=MetricType.TIMING,
                description="Average scenario completion time",
                source_table="scenarios",
                source_field="duration_seconds",
                aggregation=AggregationType.MEAN
            )
        ]
        
    async def initialize(self):
        """Initialize metrics collector"""
        await self.refresh_data()
        logger.info("Metrics collector initialized")
        
    async def refresh_data(self):
        """Refresh data from database"""
        logger.info("Refreshing metrics data from database")
        
        with self.db_manager.get_session() as session:
            # Load metrics data
            metrics = session.query(MetricsSnapshot).all()
            if metrics:
                metrics_data = [{
                    'id': m.id,
                    'total_agents': m.total_agents,
                    'active_agents': m.active_agents,
                    'total_tasks': m.total_tasks,
                    'completed_tasks': m.completed_tasks,
                    'avg_quality_score': m.avg_quality_score,
                    'avg_coordination_score': m.avg_coordination_score,
                    'agent_metrics': m.agent_metrics,
                    'task_metrics': m.task_metrics,
                    'system_metrics': m.system_metrics,
                    'created_at': m.created_at,
                    'period_start': m.period_start,
                    'period_end': m.period_end
                } for m in metrics]
                self.metrics_df = pd.DataFrame(metrics_data)
            else:
                self.metrics_df = pd.DataFrame()
                
            # Load agents data
            agents = session.query(Agent).all()
            if agents:
                agents_data = [{
                    'id': a.id,
                    'name': a.name,
                    'agent_type': a.role.value if a.role else 'unknown',
                    'status': 'active' if a.is_active else 'inactive',
                    'llm_provider': a.model_provider,
                    'created_at': a.created_at
                } for a in agents]
                self.agents_df = pd.DataFrame(agents_data)
            else:
                self.agents_df = pd.DataFrame()
                
            # Load tasks data
            tasks = session.query(Task).all()
            if tasks:
                tasks_data = [{
                    'id': t.id,
                    'agent_id': t.agent_id,
                    'task_type': t.task_type,
                    'description': t.description,
                    'status': t.status,
                    'priority': t.priority,
                    'assigned_at': t.assigned_at,
                    'started_at': t.started_at,
                    'completed_at': t.completed_at
                } for t in tasks]
                self.tasks_df = pd.DataFrame(tasks_data)
                
                # Calculate completion times
                if not self.tasks_df.empty:
                    self.tasks_df['completion_time'] = (
                        pd.to_datetime(self.tasks_df['completed_at']) - 
                        pd.to_datetime(self.tasks_df['started_at'])
                    ).dt.total_seconds() / 60  # Convert to minutes
            else:
                self.tasks_df = pd.DataFrame()
                
            # Load actions data
            actions = session.query(AgentAction).all()
            if actions:
                actions_data = [{
                    'id': a.id,
                    'agent_id': a.agent_id,
                    'task_id': a.task_id,
                    'action_type': a.action_type,
                    'description': a.description,
                    'executed_at': a.completed_at
                } for a in actions]
                self.actions_df = pd.DataFrame(actions_data)
            else:
                self.actions_df = pd.DataFrame()
                
            # Load communications data
            communications = session.query(Communication).all()
            if communications:
                comm_data = [{
                    'id': c.id,
                    'from_agent_id': c.from_agent_id,
                    'to_agent_id': c.to_agent_id,
                    'message': c.message,
                    'communication_type': c.communication_type,
                    'sent_at': c.sent_at
                } for c in communications]
                self.communications_df = pd.DataFrame(comm_data)
            else:
                self.communications_df = pd.DataFrame()
                
            # Load scenarios data
            scenarios = session.query(Scenario).all()
            if scenarios:
                scenarios_data = [{
                    'id': s.id,
                    'name': s.name,
                    'description': s.description,
                    'scenario_type': s.scenario_type,
                    'status': s.status,
                    'created_at': s.created_at
                } for s in scenarios]
                self.scenarios_df = pd.DataFrame(scenarios_data)
            else:
                self.scenarios_df = pd.DataFrame()
                
        self.last_refresh = datetime.utcnow()
        logger.info(f"Data refresh complete: {len(self.metrics_df)} metrics, {len(self.agents_df)} agents, "
                   f"{len(self.tasks_df)} tasks, {len(self.actions_df)} actions")
                   
    def calculate_metric(self, metric_def: MetricDefinition, start_time: Optional[datetime] = None, 
                        end_time: Optional[datetime] = None) -> Optional[float]:
        """Calculate a specific metric"""
        # Get appropriate dataframe
        if metric_def.source_table == "metrics":
            df = self.metrics_df
        elif metric_def.source_table == "agents":
            df = self.agents_df
        elif metric_def.source_table == "tasks":
            df = self.tasks_df
        elif metric_def.source_table == "actions":
            df = self.actions_df
        elif metric_def.source_table == "communications":
            df = self.communications_df
        elif metric_def.source_table == "scenarios":
            df = self.scenarios_df
        else:
            logger.error(f"Unknown source table: {metric_def.source_table}")
            return None
            
        if df is None or df.empty:
            return None
            
        # Apply time filters
        if start_time or end_time:
            time_col = 'timestamp' if 'timestamp' in df.columns else 'created_at'
            if time_col in df.columns:
                if start_time:
                    df = df[pd.to_datetime(df[time_col]) >= start_time]
                if end_time:
                    df = df[pd.to_datetime(df[time_col]) <= end_time]
                    
        # Apply filters
        for filter_field, filter_value in metric_def.filters.items():
            if filter_field in df.columns:
                df = df[df[filter_field] == filter_value]
                
        if df.empty:
            return None
            
        # Calculate metric based on aggregation type
        if metric_def.source_field not in df.columns:
            if metric_def.aggregation == AggregationType.COUNT:
                return len(df)
            else:
                logger.warning(f"Field {metric_def.source_field} not found in {metric_def.source_table}")
                return None
                
        values = df[metric_def.source_field].dropna()
        
        if values.empty:
            return None
            
        if metric_def.aggregation == AggregationType.MEAN:
            return float(values.mean())
        elif metric_def.aggregation == AggregationType.MEDIAN:
            return float(values.median())
        elif metric_def.aggregation == AggregationType.SUM:
            return float(values.sum())
        elif metric_def.aggregation == AggregationType.COUNT:
            return float(len(values))
        elif metric_def.aggregation == AggregationType.MIN:
            return float(values.min())
        elif metric_def.aggregation == AggregationType.MAX:
            return float(values.max())
        elif metric_def.aggregation == AggregationType.STD:
            return float(values.std())
        elif metric_def.aggregation == AggregationType.PERCENTILE_95:
            return float(values.quantile(0.95))
        elif metric_def.aggregation == AggregationType.PERCENTILE_99:
            return float(values.quantile(0.99))
        else:
            logger.error(f"Unknown aggregation type: {metric_def.aggregation}")
            return None
            
    def calculate_all_metrics(self, start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None) -> Dict[str, float]:
        """Calculate all defined metrics"""
        results = {}
        
        for metric_def in self.metric_definitions:
            try:
                value = self.calculate_metric(metric_def, start_time, end_time)
                if value is not None:
                    results[metric_def.name] = value
            except Exception as e:
                logger.error(f"Failed to calculate metric {metric_def.name}: {e}")
                
        return results
        
    def analyze_agent_performance(self) -> Dict[str, Any]:
        """Analyze individual agent performance"""
        if self.agents_df is None or self.agents_df.empty:
            return {}
            
        analysis = {
            'total_agents': len(self.agents_df),
            'agents_by_type': self.agents_df['agent_type'].value_counts().to_dict(),
            'agents_by_status': self.agents_df['status'].value_counts().to_dict(),
            'performance_by_agent': {},
            'performance_by_type': {},
            'top_performers': [],
            'improvement_needed': []
        }
        
        # Analyze task performance by agent
        if self.tasks_df is not None and not self.tasks_df.empty:
            task_stats = self.tasks_df.groupby('agent_id').agg({
                'id': 'count',
                'completion_time': 'mean',
                'status': lambda x: (x == 'completed').mean()
            }).rename(columns={
                'id': 'total_tasks',
                'completion_time': 'avg_completion_time',
                'status': 'success_rate'
            })
            
            for agent_id, stats in task_stats.iterrows():
                analysis['performance_by_agent'][agent_id] = {
                    'total_tasks': int(stats['total_tasks']),
                    'avg_completion_time': float(stats['avg_completion_time']) if pd.notna(stats['avg_completion_time']) else 0.0,
                    'success_rate': float(stats['success_rate'])
                }
                
        # Analyze performance by agent type
        if self.tasks_df is not None and not self.tasks_df.empty and self.agents_df is not None:
            # Merge tasks with agent types
            tasks_with_types = self.tasks_df.merge(
                self.agents_df[['id', 'agent_type']], 
                left_on='agent_id', 
                right_on='id',
                suffixes=('', '_agent')
            )
            
            type_stats = tasks_with_types.groupby('agent_type').agg({
                'id': 'count',
                'completion_time': 'mean',
                'status': lambda x: (x == 'completed').mean()
            }).rename(columns={
                'id': 'total_tasks',
                'completion_time': 'avg_completion_time',
                'status': 'success_rate'
            })
            
            for agent_type, stats in type_stats.iterrows():
                analysis['performance_by_type'][agent_type] = {
                    'total_tasks': int(stats['total_tasks']),
                    'avg_completion_time': float(stats['avg_completion_time']) if pd.notna(stats['avg_completion_time']) else 0.0,
                    'success_rate': float(stats['success_rate'])
                }
                
        # Identify top performers and those needing improvement
        for agent_id, perf in analysis['performance_by_agent'].items():
            score = perf['success_rate'] * 0.7 + (1.0 / max(1.0, perf['avg_completion_time'])) * 0.3
            
            agent_name = "Unknown"
            if self.agents_df is not None:
                agent_row = self.agents_df[self.agents_df['id'] == agent_id]
                if not agent_row.empty:
                    agent_name = agent_row.iloc[0]['name']
                    
            if score > 0.8:
                analysis['top_performers'].append({
                    'agent_id': agent_id,
                    'agent_name': agent_name,
                    'score': score,
                    'success_rate': perf['success_rate']
                })
            elif score < 0.5:
                analysis['improvement_needed'].append({
                    'agent_id': agent_id,
                    'agent_name': agent_name,
                    'score': score,
                    'success_rate': perf['success_rate'],
                    'avg_completion_time': perf['avg_completion_time']
                })
                
        return analysis
        
    def analyze_collaboration_patterns(self) -> Dict[str, Any]:
        """Analyze communication and collaboration patterns"""
        if self.communications_df is None or self.communications_df.empty:
            return {'total_communications': 0}
            
        analysis = {
            'total_communications': len(self.communications_df),
            'communication_frequency': {},
            'communication_network': {},
            'collaboration_effectiveness': 0.0,
            'most_communicative_agents': [],
            'communication_patterns': {}
        }
        
        # Communication frequency over time
        if 'sent_at' in self.communications_df.columns:
            self.communications_df['hour'] = pd.to_datetime(self.communications_df['sent_at']).dt.hour
            hourly_comm = self.communications_df.groupby('hour').size()
            analysis['communication_frequency'] = hourly_comm.to_dict()
            
        # Communication network analysis
        comm_network = self.communications_df.groupby(['from_agent_id', 'to_agent_id']).size()
        analysis['communication_network'] = {
            f"{from_id}->{to_id}": count 
            for (from_id, to_id), count in comm_network.items()
        }
        
        # Most communicative agents
        sender_counts = self.communications_df['from_agent_id'].value_counts()
        for agent_id, count in sender_counts.head(5).items():
            agent_name = "Unknown"
            if self.agents_df is not None and not self.agents_df.empty:
                agent_row = self.agents_df[self.agents_df['id'] == agent_id]
                if not agent_row.empty:
                    agent_name = agent_row.iloc[0]['name']
                    
            analysis['most_communicative_agents'].append({
                'agent_id': agent_id,
                'agent_name': agent_name,
                'messages_sent': int(count)
            })
            
        return analysis
        
    def analyze_scenario_outcomes(self) -> Dict[str, Any]:
        """Analyze scenario execution outcomes"""
        if self.metrics_df is None or self.metrics_df.empty:
            return {}
            
        analysis = {
            'total_scenarios': len(self.metrics_df),
            'success_rate': 0.0,
            'average_duration': 0.0,
            'average_quality': 0.0,
            'average_efficiency': 0.0,
            'outcomes_by_type': {},
            'performance_trends': {},
            'failure_analysis': []
        }
        
        # Extract metrics from metrics_data JSON
        scenario_metrics = []
        for _, row in self.metrics_df.iterrows():
            if isinstance(row['metrics_data'], dict):
                scenario_metrics.append(row['metrics_data'])
                
        if not scenario_metrics:
            return analysis
            
        # Calculate overall statistics
        completed_scenarios = [m for m in scenario_metrics if m.get('status') == 'completed']
        analysis['success_rate'] = len(completed_scenarios) / len(scenario_metrics)
        
        if completed_scenarios:
            analysis['average_duration'] = statistics.mean([
                m.get('duration_seconds', 0) for m in completed_scenarios
            ])
            analysis['average_quality'] = statistics.mean([
                m.get('quality_score', 0) for m in completed_scenarios
            ])
            analysis['average_efficiency'] = statistics.mean([
                m.get('efficiency_score', 0) for m in completed_scenarios
            ])
            
        # Analyze failures
        failed_scenarios = [m for m in scenario_metrics if m.get('status') == 'failed']
        for scenario in failed_scenarios:
            error_log = scenario.get('error_log', [])
            if error_log:
                analysis['failure_analysis'].append({
                    'scenario_id': scenario.get('scenario_id'),
                    'errors': error_log,
                    'phase': error_log[-1].get('phase', 'unknown') if error_log else 'unknown'
                })
                
        return analysis
        
    def generate_performance_charts(self) -> List[str]:
        """Generate performance visualization charts"""
        chart_paths = []
        
        try:
            # Agent performance chart
            if self.agents_df is not None and not self.agents_df.empty and self.tasks_df is not None:
                fig = self._create_agent_performance_chart()
                if fig:
                    chart_path = self.charts_dir / "agent_performance.html"
                    fig.write_html(str(chart_path))
                    chart_paths.append(str(chart_path))
                    
            # Task completion timeline
            if self.tasks_df is not None and not self.tasks_df.empty:
                fig = self._create_task_timeline_chart()
                if fig:
                    chart_path = self.charts_dir / "task_timeline.html"
                    fig.write_html(str(chart_path))
                    chart_paths.append(str(chart_path))
                    
            # Communication network
            if self.communications_df is not None and not self.communications_df.empty:
                fig = self._create_communication_network_chart()
                if fig:
                    chart_path = self.charts_dir / "communication_network.html"
                    fig.write_html(str(chart_path))
                    chart_paths.append(str(chart_path))
                    
            # Scenario outcomes
            if self.metrics_df is not None and not self.metrics_df.empty:
                fig = self._create_scenario_outcomes_chart()
                if fig:
                    chart_path = self.charts_dir / "scenario_outcomes.html"
                    fig.write_html(str(chart_path))
                    chart_paths.append(str(chart_path))
                    
        except Exception as e:
            logger.error(f"Failed to generate charts: {e}")
            
        return chart_paths
        
    def _create_agent_performance_chart(self):
        """Create agent performance visualization"""
        try:
            # Merge tasks with agent data
            tasks_with_agents = self.tasks_df.merge(
                self.agents_df[['id', 'name', 'agent_type']], 
                left_on='agent_id', 
                right_on='id',
                suffixes=('', '_agent')
            )
            
            # Calculate success rates by agent
            agent_stats = tasks_with_agents.groupby(['agent_id', 'name', 'agent_type']).agg({
                'id': 'count',
                'status': lambda x: (x == 'completed').mean()
            }).rename(columns={'id': 'total_tasks', 'status': 'success_rate'}).reset_index()
            
            # Create bar chart
            fig = px.bar(
                agent_stats,
                x='name',
                y='success_rate',
                color='agent_type',
                title='Agent Performance - Task Success Rate',
                labels={'success_rate': 'Success Rate', 'name': 'Agent Name'},
                hover_data=['total_tasks']
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Failed to create agent performance chart: {e}")
            return None
            
    def _create_task_timeline_chart(self):
        """Create task completion timeline"""
        try:
            if 'completed_at' not in self.tasks_df.columns:
                return None
                
            # Filter completed tasks
            completed_tasks = self.tasks_df[self.tasks_df['status'] == 'completed'].copy()
            if completed_tasks.empty:
                return None
                
            completed_tasks['completed_at'] = pd.to_datetime(completed_tasks['completed_at'])
            completed_tasks['date'] = completed_tasks['completed_at'].dt.date
            
            # Count tasks per day
            daily_completions = completed_tasks.groupby('date').size().reset_index(name='tasks_completed')
            
            # Create line chart
            fig = px.line(
                daily_completions,
                x='date',
                y='tasks_completed',
                title='Task Completion Timeline',
                labels={'tasks_completed': 'Tasks Completed', 'date': 'Date'}
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Failed to create task timeline chart: {e}")
            return None
            
    def _create_communication_network_chart(self):
        """Create communication network visualization"""
        try:
            # Count communications between agents
            comm_counts = self.communications_df.groupby(['from_agent_id', 'to_agent_id']).size().reset_index(name='message_count')
            
            # Get agent names
            if self.agents_df is not None and not self.agents_df.empty:
                agent_names = dict(zip(self.agents_df['id'], self.agents_df['name']))
                comm_counts['from_name'] = comm_counts['from_agent_id'].map(agent_names)
                comm_counts['to_name'] = comm_counts['to_agent_id'].map(agent_names)
            else:
                comm_counts['from_name'] = comm_counts['from_agent_id']
                comm_counts['to_name'] = comm_counts['to_agent_id']
                
            # Create network-style scatter plot
            fig = px.scatter(
                comm_counts,
                x='from_name',
                y='to_name',
                size='message_count',
                title='Agent Communication Network',
                labels={'from_name': 'From Agent', 'to_name': 'To Agent'},
                hover_data=['message_count']
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Failed to create communication network chart: {e}")
            return None
            
    def _create_scenario_outcomes_chart(self):
        """Create scenario outcomes visualization"""
        try:
            # Extract scenario data from metrics
            scenario_data = []
            for _, row in self.metrics_df.iterrows():
                if isinstance(row['metrics_data'], dict):
                    data = row['metrics_data']
                    scenario_data.append({
                        'scenario_id': data.get('scenario_id'),
                        'status': data.get('status'),
                        'duration': data.get('duration_seconds', 0),
                        'quality_score': data.get('quality_score', 0),
                        'efficiency_score': data.get('efficiency_score', 0)
                    })
                    
            if not scenario_data:
                return None
                
            df = pd.DataFrame(scenario_data)
            
            # Create scatter plot of quality vs efficiency
            fig = px.scatter(
                df,
                x='efficiency_score',
                y='quality_score',
                color='status',
                size='duration',
                title='Scenario Outcomes: Quality vs Efficiency',
                labels={'efficiency_score': 'Efficiency Score', 'quality_score': 'Quality Score'},
                hover_data=['scenario_id', 'duration']
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Failed to create scenario outcomes chart: {e}")
            return None
            
    def generate_comprehensive_report(self) -> AnalysisReport:
        """Generate comprehensive analysis report"""
        report_id = str(uuid.uuid4())
        
        # Collect all analyses
        agent_analysis = self.analyze_agent_performance()
        collaboration_analysis = self.analyze_collaboration_patterns()
        scenario_analysis = self.analyze_scenario_outcomes()
        all_metrics = self.calculate_all_metrics()
        
        # Generate charts
        chart_paths = self.generate_performance_charts()
        
        # Create findings
        findings = []
        
        # Agent performance findings
        if agent_analysis.get('total_agents', 0) > 0:
            avg_success = statistics.mean([
                perf['success_rate'] for perf in agent_analysis.get('performance_by_agent', {}).values()
            ]) if agent_analysis.get('performance_by_agent') else 0
            
            findings.append({
                'category': 'Agent Performance',
                'title': f'Overall Agent Success Rate: {avg_success:.1%}',
                'description': f"Average task success rate across {agent_analysis['total_agents']} agents",
                'severity': 'high' if avg_success < 0.7 else 'medium' if avg_success < 0.85 else 'low'
            })
            
        # Collaboration findings
        if collaboration_analysis.get('total_communications', 0) > 0:
            findings.append({
                'category': 'Collaboration',
                'title': f'{collaboration_analysis["total_communications"]} communications recorded',
                'description': 'Agent communication activity indicates collaboration levels',
                'severity': 'low'
            })
            
        # Scenario findings
        if scenario_analysis.get('total_scenarios', 0) > 0:
            findings.append({
                'category': 'Scenario Outcomes',
                'title': f'Scenario Success Rate: {scenario_analysis.get("success_rate", 0):.1%}',
                'description': f"Success rate across {scenario_analysis['total_scenarios']} scenarios",
                'severity': 'high' if scenario_analysis.get("success_rate", 0) < 0.7 else 'low'
            })
            
        # Create recommendations
        recommendations = []
        
        if agent_analysis.get('improvement_needed'):
            recommendations.append({
                'category': 'Agent Training',
                'title': 'Focus on underperforming agents',
                'description': f"{len(agent_analysis['improvement_needed'])} agents need performance improvement",
                'priority': 'high',
                'actions': [
                    'Review task assignment strategies',
                    'Provide additional training',
                    'Adjust skill requirements'
                ]
            })
            
        if collaboration_analysis.get('total_communications', 0) < 10:
            recommendations.append({
                'category': 'Collaboration',
                'title': 'Increase agent communication',
                'description': 'Low communication levels may indicate poor collaboration',
                'priority': 'medium',
                'actions': [
                    'Encourage more frequent status updates',
                    'Implement structured communication protocols',
                    'Add collaboration incentives'
                ]
            })
            
        # Create summary
        summary = f"""
        Analysis of {agent_analysis.get('total_agents', 0)} agents across {scenario_analysis.get('total_scenarios', 0)} scenarios.
        Overall system performance: {scenario_analysis.get('success_rate', 0):.1%} scenario success rate.
        Key metrics: {len(all_metrics)} performance indicators tracked.
        """
        
        report = AnalysisReport(
            report_id=report_id,
            title="Escoffier Kitchen Simulation Analysis Report",
            generated_at=datetime.utcnow(),
            summary=summary.strip(),
            findings=findings,
            recommendations=recommendations,
            visualizations=chart_paths,
            raw_data={
                'agent_analysis': agent_analysis,
                'collaboration_analysis': collaboration_analysis,
                'scenario_analysis': scenario_analysis,
                'metrics': all_metrics
            }
        )
        
        # Save report
        self._save_report(report)
        
        return report
        
    def _save_report(self, report: AnalysisReport):
        """Save analysis report to file"""
        try:
            report_file = self.reports_dir / f"analysis_report_{report.report_id}.json"
            with open(report_file, 'w') as f:
                json.dump(report.to_dict(), f, indent=2, default=str)
                
            logger.info(f"Saved analysis report to {report_file}")
            
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            
    def export_metrics_data(self, format: str = 'csv', output_path: str = None) -> str:
        """Export all metrics data"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"metrics_export_{timestamp}"
            
        try:
            if format.lower() == 'csv':
                # Export each dataframe to separate CSV files
                if self.metrics_df is not None and not self.metrics_df.empty:
                    self.metrics_df.to_csv(f"{output_path}_metrics.csv", index=False)
                if self.tasks_df is not None and not self.tasks_df.empty:
                    self.tasks_df.to_csv(f"{output_path}_tasks.csv", index=False)
                if self.communications_df is not None and not self.communications_df.empty:
                    self.communications_df.to_csv(f"{output_path}_communications.csv", index=False)
                    
            elif format.lower() == 'excel':
                output_file = f"{output_path}.xlsx"
                with pd.ExcelWriter(output_file) as writer:
                    if self.metrics_df is not None and not self.metrics_df.empty:
                        self.metrics_df.to_excel(writer, sheet_name='Metrics', index=False)
                    if self.agents_df is not None and not self.agents_df.empty:
                        self.agents_df.to_excel(writer, sheet_name='Agents', index=False)
                    if self.tasks_df is not None and not self.tasks_df.empty:
                        self.tasks_df.to_excel(writer, sheet_name='Tasks', index=False)
                    if self.communications_df is not None and not self.communications_df.empty:
                        self.communications_df.to_excel(writer, sheet_name='Communications', index=False)
                        
            logger.info(f"Exported metrics data to {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to export metrics data: {e}")
            raise
            
    def get_real_time_dashboard_data(self) -> Dict[str, Any]:
        """Get data for real-time dashboard"""
        # Refresh recent data using the sync method
        import asyncio
        try:
            asyncio.get_event_loop().run_until_complete(self.refresh_data())
        except RuntimeError:
            # If no event loop is running, create a new one
            asyncio.run(self.refresh_data())
        
        # Calculate key metrics
        metrics = self.calculate_all_metrics()
        agent_analysis = self.analyze_agent_performance()
        collaboration_analysis = self.analyze_collaboration_patterns()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'key_metrics': metrics,
            'agent_summary': {
                'total_agents': agent_analysis.get('total_agents', 0),
                'top_performers': len(agent_analysis.get('top_performers', [])),
                'improvement_needed': len(agent_analysis.get('improvement_needed', []))
            },
            'collaboration_summary': {
                'total_communications': collaboration_analysis.get('total_communications', 0),
                'most_active_agents': len(collaboration_analysis.get('most_communicative_agents', []))
            },
            'system_health': {
                'data_freshness': (datetime.utcnow() - self.last_refresh).total_seconds() if self.last_refresh else 0,
                'data_completeness': sum([
                    1 for df in [self.metrics_df, self.agents_df, self.tasks_df]
                    if df is not None and not df.empty
                ]) / 3
            }
        }

    def export_to_csv(self, output_dir: str) -> list[str]:
        """Export all metrics data to CSV files with enhanced analytics"""
        import os
        from datetime import datetime
        import pandas as pd
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_files = []
        
        # Create analytics subdirectory
        analytics_dir = os.path.join(output_dir, "analytics")
        os.makedirs(analytics_dir, exist_ok=True)
        
        # Export enhanced agents data
        if self.agents_df is not None and not self.agents_df.empty:
            agents_file = os.path.join(analytics_dir, f"agents_{timestamp}.csv")
            # Ensure all important columns are present
            enhanced_agents = self.agents_df.copy()
            if 'llm_provider' not in enhanced_agents.columns:
                enhanced_agents['llm_provider'] = 'unknown'
            if 'agent_type' not in enhanced_agents.columns:
                enhanced_agents['agent_type'] = 'unknown'
            enhanced_agents.to_csv(agents_file, index=False)
            csv_files.append(agents_file)
        
        # Export enhanced tasks data with agent context
        if self.tasks_df is not None and not self.tasks_df.empty:
            tasks_enhanced = self.tasks_df.copy()
            
            # Merge with agent data if available
            if self.agents_df is not None and 'agent_id' in tasks_enhanced.columns:
                tasks_enhanced = tasks_enhanced.merge(
                    self.agents_df[['id', 'name', 'agent_type', 'llm_provider']], 
                    left_on='agent_id', 
                    right_on='id', 
                    how='left',
                    suffixes=('_task', '_agent')
                )
                # Rename columns for clarity
                if 'name_agent' in tasks_enhanced.columns:
                    tasks_enhanced.rename(columns={'name_agent': 'agent_name'}, inplace=True)
                if 'id_agent' in tasks_enhanced.columns:
                    tasks_enhanced.drop(columns=['id_agent'], inplace=True)
            
            tasks_file = os.path.join(analytics_dir, f"tasks_{timestamp}.csv")
            tasks_enhanced.to_csv(tasks_file, index=False)
            csv_files.append(tasks_file)
        
        # Export actions data with enhanced context
        if self.actions_df is not None and not self.actions_df.empty:
            actions_enhanced = self.actions_df.copy()
            
            # Merge with agent data if available
            if self.agents_df is not None and 'agent_id' in actions_enhanced.columns:
                actions_enhanced = actions_enhanced.merge(
                    self.agents_df[['id', 'name', 'agent_type', 'llm_provider']], 
                    left_on='agent_id', 
                    right_on='id', 
                    how='left',
                    suffixes=('_action', '_agent')
                )
                if 'name_agent' in actions_enhanced.columns:
                    actions_enhanced.rename(columns={'name_agent': 'agent_name'}, inplace=True)
                if 'id_agent' in actions_enhanced.columns:
                    actions_enhanced.drop(columns=['id_agent'], inplace=True)
            
            actions_file = os.path.join(analytics_dir, f"actions_{timestamp}.csv")
            actions_enhanced.to_csv(actions_file, index=False)
            csv_files.append(actions_file)
        
        # Export calculated metrics
        if hasattr(self, 'metrics_df') and self.metrics_df is not None and not self.metrics_df.empty:
            metrics_file = os.path.join(analytics_dir, f"metrics_{timestamp}.csv")
            self.metrics_df.to_csv(metrics_file, index=False)
            csv_files.append(metrics_file)
        
        # Export comprehensive summary metrics with provider/type breakdowns
        summary_metrics = self.calculate_all_metrics()
        
        # Add provider-specific metrics
        if self.agents_df is not None and not self.agents_df.empty:
            provider_stats = self.agents_df['llm_provider'].value_counts().to_dict()
            for provider, count in provider_stats.items():
                summary_metrics[f'agents_provider_{provider}'] = count
                
            type_stats = self.agents_df['agent_type'].value_counts().to_dict()
            for agent_type, count in type_stats.items():
                summary_metrics[f'agents_type_{agent_type}'] = count
        
        # Add task performance by provider/type
        if self.tasks_df is not None and self.agents_df is not None and 'agent_id' in self.tasks_df.columns:
            task_agent_df = self.tasks_df.merge(
                self.agents_df[['id', 'agent_type', 'llm_provider']], 
                left_on='agent_id', 
                right_on='id', 
                how='left'
            )
            
            # Provider performance metrics
            provider_task_stats = task_agent_df.groupby(['llm_provider', 'status']).size().unstack(fill_value=0)
            for provider in provider_task_stats.index:
                for status in provider_task_stats.columns:
                    summary_metrics[f'tasks_{provider}_{status}'] = provider_task_stats.loc[provider, status]
            
            # Agent type performance metrics
            type_task_stats = task_agent_df.groupby(['agent_type', 'status']).size().unstack(fill_value=0)
            for agent_type in type_task_stats.index:
                for status in type_task_stats.columns:
                    summary_metrics[f'tasks_{agent_type}_{status}'] = type_task_stats.loc[agent_type, status]
        
        # Export enhanced summary
        summary_file = os.path.join(analytics_dir, f"summary_metrics_{timestamp}.csv")
        summary_df = pd.DataFrame(list(summary_metrics.items()), columns=['metric', 'value'])
        summary_df.to_csv(summary_file, index=False)
        csv_files.append(summary_file)
        
        # Export provider-agent matrix for analysis
        if self.agents_df is not None and not self.agents_df.empty:
            provider_type_matrix = self.agents_df.groupby(['llm_provider', 'agent_type']).size().reset_index(name='count')
            matrix_file = os.path.join(analytics_dir, f"provider_agent_matrix_{timestamp}.csv")
            provider_type_matrix.to_csv(matrix_file, index=False)
            csv_files.append(matrix_file)
        
        return csv_files

    def generate_charts(self, output_dir: str) -> list[str]:
        """Generate visualization charts with enhanced analytics"""
        import os
        from datetime import datetime
        
        try:
            import plotly.graph_objects as go
            import plotly.express as px
            from plotly.subplots import make_subplots
        except ImportError:
            logger.warning("Plotly not available. Installing plotly with: pip install plotly")
            # Fallback to basic text-based charts
            return self._generate_text_charts(output_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chart_files = []
        
        # Create charts subdirectory
        charts_dir = os.path.join(output_dir, "charts")
        os.makedirs(charts_dir, exist_ok=True)
        
        # 1. Enhanced Agent performance chart with provider info
        if self.agents_df is not None and not self.agents_df.empty:
            # Agent performance by provider and type
            fig = px.sunburst(
                self.agents_df,
                path=['llm_provider', 'agent_type', 'name'],
                title='Agent Distribution by Provider and Type',
                color='agent_type'
            )
            agent_chart = os.path.join(charts_dir, f"agents_hierarchy_{timestamp}.html")
            fig.write_html(agent_chart)
            chart_files.append(agent_chart)
            
            # Provider vs Agent Type matrix
            if 'llm_provider' in self.agents_df.columns and 'agent_type' in self.agents_df.columns:
                provider_type_matrix = self.agents_df.groupby(['llm_provider', 'agent_type']).size().reset_index(name='count')
                fig = px.bar(
                    provider_type_matrix,
                    x='llm_provider',
                    y='count',
                    color='agent_type',
                    title='Agent Count by Provider and Type',
                    labels={'count': 'Number of Agents', 'llm_provider': 'LLM Provider'}
                )
                matrix_chart = os.path.join(charts_dir, f"provider_type_matrix_{timestamp}.html")
                fig.write_html(matrix_chart)
                chart_files.append(matrix_chart)
        
        # 2. Enhanced Task analytics with agent context
        if self.tasks_df is not None and not self.tasks_df.empty:
            # Task status distribution
            status_counts = self.tasks_df['status'].value_counts()
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title='Task Status Distribution',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            task_chart = os.path.join(charts_dir, f"task_status_chart_{timestamp}.html")
            fig.write_html(task_chart)
            chart_files.append(task_chart)
            
            # Task performance by agent if we have agent info
            if 'agent_id' in self.tasks_df.columns and self.agents_df is not None:
                # Merge tasks with agent info
                task_agent_df = self.tasks_df.merge(
                    self.agents_df[['id', 'name', 'agent_type', 'llm_provider']], 
                    left_on='agent_id', 
                    right_on='id', 
                    how='left',
                    suffixes=('_task', '_agent')
                )
                
                if not task_agent_df.empty:
                    # Task completion by provider
                    provider_task_stats = task_agent_df.groupby(['llm_provider', 'status']).size().reset_index(name='count')
                    fig = px.bar(
                        provider_task_stats,
                        x='llm_provider',
                        y='count',
                        color='status',
                        title='Task Performance by LLM Provider',
                        labels={'count': 'Number of Tasks', 'llm_provider': 'LLM Provider'}
                    )
                    provider_perf_chart = os.path.join(charts_dir, f"provider_performance_{timestamp}.html")
                    fig.write_html(provider_perf_chart)
                    chart_files.append(provider_perf_chart)
                    
                    # Task completion by agent type
                    type_task_stats = task_agent_df.groupby(['agent_type', 'status']).size().reset_index(name='count')
                    fig = px.bar(
                        type_task_stats,
                        x='agent_type',
                        y='count',
                        color='status',
                        title='Task Performance by Agent Type',
                        labels={'count': 'Number of Tasks', 'agent_type': 'Agent Type'}
                    )
                    type_perf_chart = os.path.join(charts_dir, f"agent_type_performance_{timestamp}.html")
                    fig.write_html(type_perf_chart)
                    chart_files.append(type_perf_chart)
        
        # 3. Agent type distribution (enhanced)
        if self.agents_df is not None and not self.agents_df.empty:
            type_counts = self.agents_df['agent_type'].value_counts()
            fig = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                title='Agent Type Distribution',
                hole=0.4  # Donut chart for better visibility
            )
            agent_type_chart = os.path.join(charts_dir, f"agent_types_chart_{timestamp}.html")
            fig.write_html(agent_type_chart)
            chart_files.append(agent_type_chart)
        
        # 4. Enhanced Provider analytics
        if self.agents_df is not None and not self.agents_df.empty:
            provider_counts = self.agents_df['llm_provider'].value_counts()
            fig = px.bar(
                x=provider_counts.index,
                y=provider_counts.values,
                title='LLM Provider Distribution',
                labels={'x': 'Provider', 'y': 'Agent Count'},
                color=provider_counts.values,
                color_continuous_scale='viridis'
            )
            provider_chart = os.path.join(charts_dir, f"providers_chart_{timestamp}.html")
            fig.write_html(provider_chart)
            chart_files.append(provider_chart)
        
        # 5. Task timeline with agent context
        if self.tasks_df is not None and not self.tasks_df.empty and 'created_at' in self.tasks_df.columns:
            if self.agents_df is not None and 'agent_id' in self.tasks_df.columns:
                # Enhanced timeline with agent info
                task_agent_df = self.tasks_df.merge(
                    self.agents_df[['id', 'name', 'agent_type', 'llm_provider']], 
                    left_on='agent_id', 
                    right_on='id', 
                    how='left',
                    suffixes=('_task', '_agent')
                )
                
                if not task_agent_df.empty:
                    fig = px.scatter(
                        task_agent_df,
                        x='created_at',
                        y='id_task',
                        color='llm_provider',
                        symbol='agent_type',
                        title='Task Timeline by Provider and Agent Type',
                        labels={'created_at': 'Time', 'id_task': 'Task ID'},
                        hover_data=['name', 'status', 'task_type']
                    )
                    timeline_chart = os.path.join(charts_dir, f"task_timeline_enhanced_{timestamp}.html")
                    fig.write_html(timeline_chart)
                    chart_files.append(timeline_chart)
            else:
                # Basic timeline
                fig = px.scatter(
                    self.tasks_df,
                    x='created_at',
                    y='id',
                    color='status',
                    title='Task Timeline',
                    labels={'created_at': 'Time', 'id': 'Task ID'}
                )
                timeline_chart = os.path.join(charts_dir, f"task_timeline_{timestamp}.html")
                fig.write_html(timeline_chart)
                chart_files.append(timeline_chart)
        
        # 6. Performance efficiency metrics
        if hasattr(self, 'metrics_df') and self.metrics_df is not None and not self.metrics_df.empty:
            # Metrics over time
            metrics_over_time = self.metrics_df.melt(
                id_vars=['scenario_id', 'created_at'],
                value_vars=[col for col in self.metrics_df.columns if col.endswith('_score')],
                var_name='metric_type',
                value_name='score'
            )
            
            if not metrics_over_time.empty:
                fig = px.line(
                    metrics_over_time,
                    x='created_at',
                    y='score',
                    color='metric_type',
                    title='Performance Metrics Over Time',
                    labels={'score': 'Score', 'created_at': 'Time'}
                )
                metrics_chart = os.path.join(charts_dir, f"performance_metrics_{timestamp}.html")
                fig.write_html(metrics_chart)
                chart_files.append(metrics_chart)
        
        return chart_files

    def _generate_text_charts(self, output_dir: str) -> list[str]:
        """Generate text-based charts as fallback"""
        import os
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chart_files = []
        
        # Generate text-based summary
        summary_file = os.path.join(output_dir, f"metrics_summary_{timestamp}.txt")
        
        with open(summary_file, 'w') as f:
            f.write("ESCOFFIER METRICS SUMMARY\n")
            f.write("=" * 40 + "\n\n")
            
            # Agent statistics
            if self.agents_df is not None and not self.agents_df.empty:
                f.write("AGENT STATISTICS:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Total agents: {len(self.agents_df)}\n")
                
                type_counts = self.agents_df['agent_type'].value_counts()
                f.write("\nAgent types:\n")
                for agent_type, count in type_counts.items():
                    f.write(f"  {agent_type}: {count}\n")
                
                provider_counts = self.agents_df['llm_provider'].value_counts()
                f.write("\nLLM providers:\n")
                for provider, count in provider_counts.items():
                    f.write(f"  {provider}: {count}\n")
                f.write("\n")
            
            # Task statistics
            if self.tasks_df is not None and not self.tasks_df.empty:
                f.write("TASK STATISTICS:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Total tasks: {len(self.tasks_df)}\n")
                
                status_counts = self.tasks_df['status'].value_counts()
                f.write("\nTask status:\n")
                for status, count in status_counts.items():
                    f.write(f"  {status}: {count}\n")
                f.write("\n")
            
            # System metrics
            metrics = self.calculate_all_metrics()
            f.write("SYSTEM METRICS:\n")
            f.write("-" * 20 + "\n")
            for metric_name, value in metrics.items():
                f.write(f"{metric_name}: {value:.3f}\n")
        
        chart_files.append(summary_file)
        logger.info(f"Generated text-based metrics summary: {summary_file}")
        
        return chart_files