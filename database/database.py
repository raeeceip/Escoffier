"""
Database Layer for ChefBench
Handles persistent storage of agents, scenarios, and metrics

I'll fix you later
"""

import sqlite3
import json
import pickle
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ChefBenchDatabase:
    """SQLite database for persistent storage"""
    
    def __init__(self, db_path: str = "chefbench.db"):
        self.db_path = Path(db_path)
        self.connection = None
        self.initialize_database()
    
    def initialize_database(self):
        """Create database tables if they don't exist"""
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row

        cursor = self.connection.cursor()
        
        # Agents table - stores actual agent configurations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                model_name TEXT NOT NULL,
                model_config TEXT NOT NULL,
                tokenizer_config TEXT NOT NULL,
                available_tasks TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP,
                total_tasks_completed INTEGER DEFAULT 0,
                total_messages_sent INTEGER DEFAULT 0,
                average_quality_score REAL DEFAULT 0.0,
                authority_compliance REAL DEFAULT 1.0,
                model_weights_path TEXT,
                cache_dir TEXT
            )
        """)
        
        # Agent states - stores runtime state for recovery
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_states (
                state_id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                message_queue TEXT,
                sent_messages TEXT,
                task_history TEXT,
                collaboration_score REAL DEFAULT 0.0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
            )
        """)
        
        # Scenarios table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scenarios (
                scenario_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                configuration TEXT NOT NULL,
                tasks TEXT NOT NULL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'pending',
                duration_seconds REAL,
                participating_agents TEXT NOT NULL
            )
        """)
        
        # Task executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_executions (
                execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                start_time TIMESTAMP,
                reasoning_time REAL,
                execution_time REAL,
                chosen_approach TEXT,
                resources_used TEXT,
                collaboration_agents TEXT,
                success BOOLEAN,
                quality_score REAL,
                FOREIGN KEY (scenario_id) REFERENCES scenarios (scenario_id),
                FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id TEXT,
                sender_id TEXT NOT NULL,
                recipient_id TEXT NOT NULL,
                content TEXT NOT NULL,
                task_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                requires_response BOOLEAN,
                priority INTEGER,
                FOREIGN KEY (scenario_id) REFERENCES scenarios (scenario_id),
                FOREIGN KEY (sender_id) REFERENCES agents (agent_id),
                FOREIGN KEY (recipient_id) REFERENCES agents (agent_id)
            )
        """)
        
        # Metrics snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id TEXT NOT NULL,
                agent_id TEXT,
                metric_type TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (scenario_id) REFERENCES scenarios (scenario_id),
                FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
            )
        """)
        
        # Model cache table - stores downloaded model information
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_cache (
                model_name TEXT PRIMARY KEY,
                cache_path TEXT NOT NULL,
                model_size_mb REAL,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                use_count INTEGER DEFAULT 0
            )
        """)
        
        self.connection.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def connect(self):
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Connected to database at {self.db_path}")

        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            self.connection =  None
 
        finally :
            return self.close()
            

    def save_agent(self, agent_data: Dict[str, Any]) -> bool:
        """Save agent to database"""
        try:
            if not self.connection:
                logger.error("Database connection is not established.")
            else:
                cursor = self.connection.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO agents (
                        agent_id, name, role, model_name, model_config,
                        tokenizer_config, available_tasks, last_active,
                        model_weights_path, cache_dir
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    agent_data['agent_id'],
                    agent_data['name'],
                    agent_data['role'],
                    agent_data['model_name'],
                    json.dumps(agent_data.get('model_config', {})),
                    json.dumps(agent_data.get('tokenizer_config', {})),
                    json.dumps(agent_data.get('available_tasks', [])),
                    datetime.now().isoformat(),
                    agent_data.get('model_weights_path'),
                    agent_data.get('cache_dir')
                ))
                self.connection.commit()
            logger.info(f"Saved agent {agent_data['name']} to database")
            return True
        except Exception as e:
            logger.error(f"Failed to save agent: {e}")
            if self.connection:
                self.connection.rollback()
                self.connection = None
            return False
        
        finally:
            if self.connection:
                self.connection.close()
            
    
    def load_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Load agent from database"""
        try:
            if not self.connection: 
                logger.error("Database connection is not established.")
            else : 
       
                    cursor = self.connection.cursor()
                    cursor.execute("""
                        SELECT * FROM agents WHERE name = ?
                    """, (agent_name,))
                    
                    row = cursor.fetchone()
                    if row:
                        return {
                            'agent_id': row['agent_id'],
                            'name': row['name'],
                            'role': row['role'],
                            'model_name': row['model_name'],
                            'model_config': json.loads(row['model_config']),
                            'tokenizer_config': json.loads(row['tokenizer_config']),
                            'available_tasks': json.loads(row['available_tasks']),
                            'created_at': row['created_at'],
                            'last_active': row['last_active'],
                            'total_tasks_completed': row['total_tasks_completed'],
                            'average_quality_score': row['average_quality_score'],
                            'authority_compliance': row['authority_compliance'],
                            'model_weights_path': row['model_weights_path'],
                            'cache_dir': row['cache_dir']
                        }
                    return None

        except Exception as e:
                logger.error(f"Failed to load agent: {e}")
                if self.connection:
                    self.connection.rollback()
                    self.connection = None
                return None
        


        finally:
            if self.connection:
                self.connection.close()

    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get all agents from database"""
        """ check if exists first before connection, can be none """
        if not self.connection:
            logger.error("Database connection is not established.")
            return []
        else: 
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM agents ORDER BY created_at DESC")

        
        agents = []
        for row in cursor.fetchall():
            agents.append({
                'agent_id': row['agent_id'],
                'name': row['name'],
                'role': row['role'],
                'model_name': row['model_name'],
                'created_at': row['created_at'],
                'total_tasks_completed': row['total_tasks_completed'],
                'average_quality_score': row['average_quality_score']
            })
        return agents
    
    def save_agent_state(self, agent_id: str, state_data: Dict[str, Any]):
        """Save agent runtime state for recovery"""

        if not self.connection:
            logger.error("Database connection is not established.")
            return None
        else:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO agent_states (
                    agent_id, message_queue, sent_messages,
                    task_history, collaboration_score
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                agent_id,
                json.dumps(state_data.get('message_queue', [])),
                json.dumps(state_data.get('sent_messages', [])),
                json.dumps(state_data.get('task_history', [])),
                state_data.get('collaboration_score', 0.0)
            ))
            self.connection.commit()
    
    def load_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Load most recent agent state"""
        if not self.connection:
            logger.error("Database connection is not established.")
            return None
        else :
                
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM agent_states 
                WHERE agent_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (agent_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'message_queue': json.loads(row['message_queue']),
                    'sent_messages': json.loads(row['sent_messages']),
                    'task_history': json.loads(row['task_history']),
                    'collaboration_score': row['collaboration_score'],
                    'timestamp': row['timestamp']
                }
            return None
        
    def save_scenario(self, scenario_data: Dict[str, Any]) -> bool:
        """Save scenario to database"""
        if not self.connection:
            logger.error("Database connection is not established.")
            return False

        try:
            if not self.connection:
                logger.error("Database connection is not established.")
                return False
            
            else:
                cursor = self.connection.cursor()
                cursor.execute("""
                    INSERT INTO scenarios (
                        scenario_id, name, type, configuration,
                    tasks, started_at, status, participating_agents
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scenario_data['scenario_id'],
                scenario_data['name'],
                scenario_data['type'],
                json.dumps(scenario_data['configuration']),
                json.dumps(scenario_data['tasks']),
                datetime.now().isoformat(),
                'running',
                json.dumps(scenario_data['participating_agents'])
            ))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save scenario: {e}")
            self.connection.rollback()
            return False
        finally:
            if self.connection:
                self.connection.close() 
        

    
    def update_scenario_status(
        self, 
        scenario_id: str, 
        status: str, 
        duration: Optional[float] = None
    ):
        if not self.connection:
            logger.error("Database connection is not established.")
            return None

        """Update scenario completion status"""
        cursor = self.connection.cursor()
        if duration:
            cursor.execute("""
                UPDATE scenarios 
                SET status = ?, completed_at = ?, duration_seconds = ?
                WHERE scenario_id = ?
            """, (status, datetime.now().isoformat(), duration, scenario_id))
        else:
            cursor.execute("""
                UPDATE scenarios 
                SET status = ?
                WHERE scenario_id = ?
            """, (status, scenario_id))
        self.connection.commit()
    
    def save_task_execution(self, execution_data: Dict[str, Any]):
        """Save task execution record"""
        if not self.connection:
            logger.error("Database connection is not established.")
            return None

        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO task_executions (
                scenario_id, agent_id, task_type, start_time,
                reasoning_time, execution_time, chosen_approach,
                resources_used, collaboration_agents, success, quality_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution_data['scenario_id'],
            execution_data['agent_id'],
            execution_data['task_type'],
            execution_data['start_time'],
            execution_data['reasoning_time'],
            execution_data['execution_time'],
            execution_data['chosen_approach'],
            json.dumps(execution_data.get('resources_used', [])),
            json.dumps(execution_data.get('collaboration_agents', [])),
            execution_data['success'],
            execution_data['quality_score']
        ))
        self.connection.commit()
    
    def save_message(self, message_data: Dict[str, Any]):
        """Save inter-agent message"""
        if not self.connection:
            logger.error("Database connection is not established.")
            return None
        
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO messages (
                scenario_id, sender_id, recipient_id, content,
                task_type, requires_response, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            message_data.get('scenario_id'),
            message_data['sender_id'],
            message_data['recipient_id'],
            message_data['content'],
            message_data.get('task_type'),
            message_data.get('requires_response', False),
            message_data.get('priority', 3)
        ))
        self.connection.commit()
    
    def save_metric(
        self, 
        scenario_id: str,
        metric_type: str,
        metric_name: str,
        metric_value: float,
        agent_id: Optional[str] = None
    ):
        """Save performance metric"""
        if not self.connection:
            logger.error("Database Connection is not established.")
            return None 
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO metrics (
                scenario_id, agent_id, metric_type,
                metric_name, metric_value
            ) VALUES (?, ?, ?, ?, ?)
        """, (scenario_id, agent_id, metric_type, metric_name, metric_value))
        self.connection.commit()
    
    def get_scenario_metrics(self, scenario_id: str) -> List[Dict[str, Any]]:
        """Get all metrics for a scenario"""

        if not self.connection:
            logger.error("Database connection is not established.")
            return []
        else:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM metrics 
                WHERE scenario_id = ?
                ORDER BY timestamp
            """, (scenario_id,))
            
            metrics = []
            for row in cursor.fetchall():
                metrics.append({
                    'metric_type': row['metric_type'],
                    'metric_name': row['metric_name'],
                    'metric_value': row['metric_value'],
                    'agent_id': row['agent_id'],
                    'timestamp': row['timestamp']
                })
            return metrics
    
    def get_agent_performance_history(self, agent_id: str) -> Dict[str, Any]:
        """Get complete performance history for an agent"""

        if not self.connection:
            logger.error("Database connection is not established.")
            return {}
        else :
            cursor = self.connection.cursor()
            
            # Get task executions
            cursor.execute("""
                SELECT * FROM task_executions
                WHERE agent_id = ?
                ORDER BY start_time DESC
            """, (agent_id,))
            
            executions = []
            for row in cursor.fetchall():
                executions.append({
                    'task_type': row['task_type'],
                    'success': row['success'],
                    'quality_score': row['quality_score'],
                    'reasoning_time': row['reasoning_time'],
                    'execution_time': row['execution_time']
                })
            
            # Get message history
            cursor.execute("""
                SELECT COUNT(*) as sent_count 
                FROM messages 
                WHERE sender_id = ?
            """, (agent_id,))
            sent_count = cursor.fetchone()['sent_count']
            
            cursor.execute("""
                SELECT COUNT(*) as received_count 
                FROM messages 
                WHERE recipient_id = ?
            """, (agent_id,))
            received_count = cursor.fetchone()['received_count']
            
            return {
                'agent_id': agent_id,
                'total_executions': len(executions),
                'successful_executions': sum(1 for e in executions if e['success']),
                'average_quality': sum(e['quality_score'] for e in executions) / max(len(executions), 1),
                'messages_sent': sent_count,
                'messages_received': received_count,
                'execution_history': executions
            }
    
    def update_model_cache(self, model_name: str, cache_path: str, size_mb: float):
        """Update model cache information""" 
        if not self.connection:
            logger.error("Database connection is not established.")
            return []
    
        cursor = self.connection.cursor()
        cursor.execute("""
                    INSERT OR REPLACE INTO model_cache (
                        model_name, cache_path, model_size_mb, last_used, use_count
                    ) VALUES (
                        ?, ?, ?, ?, 
                        COALESCE((SELECT use_count + 1 FROM model_cache WHERE model_name = ?), 1)
                    )
                """, (model_name, cache_path, size_mb, datetime.now().isoformat(), model_name))
        self.connection.commit()
    
    def get_cached_models(self) -> List[Dict[str, Any]]:
        """Get list of cached models"""
        if not self.connection:
            logger.error("Database connection is not established.")
            return []
        else:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM model_cache
                ORDER BY last_used DESC
            """)
            
            models = []
            for row in cursor.fetchall():
                models.append({
                    'model_name': row['model_name'],
                    'cache_path': row['cache_path'],
                    'size_mb': row['model_size_mb'],
                    'download_date': row['download_date'],
                    'last_used': row['last_used'],
                    'use_count': row['use_count']
                })
            return models
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def rollback(self):
        """Rollback current transaction"""
        if self.connection:
            self.connection.rollback()
            logger.info("Database transaction rolled back")