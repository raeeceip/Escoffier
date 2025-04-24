# MasterChef-Bench: System Design & Implementation Requirements

## Overview

MasterChef-Bench is a multi-agent benchmark system for testing LLM coherence and coordination in a simulated kitchen environment. This document outlines the system architecture, technology choices, and implementation requirements across three key components: the backend API, frontend monitoring interface, and agent deployment infrastructure.

## System Architecture

```
+--------------------------------+
|       Frontend Application      |
|   (React + TypeScript + D3.js)  |
+----------------+---------------+
                 |
                 | HTTPS/WebSockets
                 |
+----------------v---------------+     +------------------------+
|                                |     |                        |
|        Kitchen API Server      |     |  Cloudflare Workers    |
|            (Backend)           <----->  (Agent Execution)     |
|                                |     |                        |
+----------------+---------------+     +------------------------+
                 |
                 | Database Operations
                 |
+----------------v---------------+     +------------------------+
|                                |     |                        |
|       PostgreSQL Database      |     |    Linode Server       |
|                                |     |  (Ollama Model Host)   |
+--------------------------------+     +------------------------+
```

## 1. Backend API Requirements

### Technology Stack
- **Primary Language**: Go (Golang) for performance and concurrency
- **Alternative Option**: Node.js with TypeScript (if rapid development is prioritized)
- **Framework**: Gin (Go) or Express/Fastify (Node.js)
- **Database**: PostgreSQL with proper indexes and JSON capabilities
- **Authentication**: JWT with role-based access control
- **Real-time**: WebSockets for live updates
- **Documentation**: OpenAPI/Swagger

### Core API Modules

#### Kitchen State Management
- Database schema for kitchen inventory, equipment, and status
- Transactional operations for all kitchen actions
- Time simulation system with configurable speed

#### Agent Interaction
- Role-based API endpoints with proper authorization
- Action validation based on kitchen rules
- Communication channels between agents

#### Evaluation System
- Comprehensive logging of all agent actions
- Metrics collection for coherence and performance
- Session management for experiment tracking

### API Deployment
- Containerized using Docker
- Deployed alongside frontend on Linode server
- Autoscaling capabilities for handling multiple simultaneous benchmarks

## 2. Frontend Application Requirements

### Technology Stack
- **Framework**: React with TypeScript
- **State Management**: Redux Toolkit or Zustand
- **Styling**: Tailwind CSS
- **Visualization**: D3.js for kitchen state visualization
- **Real-time**: Socket.io or native WebSockets
- **UI Components**: Material UI or Chakra UI

### Core Frontend Modules

#### Kitchen Visualization
- Real-time view of kitchen state
- 2D or 3D visualization of agent movements and actions
- Timeline of kitchen activities

#### Agent Monitoring
- Agent status dashboard
- Communication logs between agents
- Performance metrics visualization

#### Benchmark Control
- Session creation and configuration
- Model uploading interface (connecting to Ollama)
- Scenario configuration and execution
- Results analysis and export

### Frontend Deployment
- Static site hosted on Cloudflare Pages
- Optimized bundle with code splitting
- Responsive design for various screen sizes

## 3. Agent Architecture Requirements

### Technology Stack
- **Primary Platform**: Cloudflare Workers
- **Execution Environment**: Edge computing
- **Language**: TypeScript with Cloudflare Workers SDK
- **LLM Integration**: Ollama API interface
- **State Management**: Durable Objects or KV for agent memory

### Agent Framework Components

#### Core Agent Interface
- Standard API client for Kitchen API communication
- Role-specific prompting and constraints
- Context management for tracking conversation history
- Memory systems (vector/key-value) for long-term coherence

#### Role-Specific Agents
- Executive Chef: Strategic planning and oversight
- Sous Chef: Operational management
- Chef de Partie: Station management
- Line Cook: Execution of specific cooking tasks
- Prep Cook: Ingredient preparation
- Kitchen Porter: Cleaning and maintenance

#### Agent Deployment System
- Llamafile upload processing
- Worker deployment configuration
- Model weight assignment to Ollama instances

## 4. Integration & Communication

### API ↔ Frontend
- REST API for CRUD operations
- WebSockets for real-time updates
- Authentication using JWT
- File uploads via Cloudflare Stream

### API ↔ Agent
- REST API for agent actions
- WebSockets for real-time kitchen updates
- Role-based access control
- Rate limiting for fair simulation

### Agent ↔ Model Host
- Secure communication with Ollama API
- Model version management
- Input/output streaming for responsive interactions

### Frontend ↔ Model Host
- Direct file uploads to Ollama via secure proxy
- Model configuration interface
- Status monitoring

## 5. Deployment Strategy

### Linode Server Configuration
- 8+ Core CPU, 32GB+ RAM for multiple Ollama models
- SSD storage for database and model weights
- Docker Compose for service orchestration
- Nginx for reverse proxy and SSL termination
- Automated backups

### Cloudflare Integration
- Cloudflare Workers for agent deployment
- Cloudflare Pages for frontend hosting
- Workers KV for agent state storage
- Cloudflare Access for secure administration

### Scaling Considerations
- Multiple Linode instances for larger experiments
- Database sharding for high-volume metrics
- Worker scaling for large agent counts
- Cache strategies for reducing database load

## 6. Security Requirements

- JWT authentication with proper expiration
- HTTPS for all connections
- Role-based access control for API endpoints
- Input validation and sanitization
- Rate limiting for API access
- Secure model weight handling
- Regular security audits

## 7. Implementation Roadmap

### Phase 1: Core Infrastructure
- Set up Linode server with Docker
- Create basic API with database schema
- Implement authentication system
- Develop simple monitoring frontend

### Phase 2: Kitchen Simulation
- Implement kitchen state management
- Create time simulation system
- Develop basic agent framework
- Build visualization components

### Phase 3: Agent Development
- Implement Cloudflare Worker agents
- Create role-specific agent behaviors
- Set up Ollama integration
- Develop agent memory systems

### Phase 4: Evaluation & Testing
- Implement metrics collection
- Create benchmark scenarios
- Develop evaluation dashboards
- Test with multiple LLM models

## 8. Technical Challenges & Considerations

### Long-Term Coherence
- Agent memory systems must balance detail and efficiency
- Context window management for LLMs
- Strategies for summarizing historical interactions

### Multi-Agent Coordination
- Preventing deadlocks in resource allocation
- Managing communication overhead
- Ensuring consistent world state across agents

### Performance Optimization
- Efficient database queries for real-time updates
- Parallelizing agent executions
- Minimizing latency in agent-model communication

### Scalability
- Running multiple sessions simultaneously
- Supporting different LLM models
- Handling high volumes of evaluation data

## 9. Required Tools & Resources

- **Development Environment**: Docker, Git, VS Code
- **CI/CD Pipeline**: GitHub Actions
- **Cloud Resources**: Linode account, Cloudflare account
- **Monitoring**: Prometheus, Grafana (optional)
- **LLM Models**: Access to various models for testing

---

This design document provides a comprehensive overview of the MasterChef-Bench system architecture and implementation requirements. The modular approach allows for parallel development of the backend, frontend, and agent components, with clear integration points between them. The use of Cloudflare Workers for agent deployment provides flexibility and scalability, while the Linode server with Ollama offers a cost-effective solution for model hosting.

## How It Works

### Setting Up the Backend API

1. **Install Go**: Ensure you have Go installed on your machine.
2. **Clone the Repository**: `git clone https://github.com/raeeceip/masterchef.git`
3. **Navigate to Backend Directory**: `cd masterchef/backend`
4. **Install Dependencies**: `go get ./...`
5. **Set Up PostgreSQL Database**: Ensure you have a PostgreSQL database running and update the connection details in `main.go`.
6. **Run the Server**: `go run main.go`

### Setting Up the Frontend Application

1. **Install Node.js and npm**: Ensure you have Node.js and npm installed on your machine.
2. **Navigate to Frontend Directory**: `cd masterchef/frontend`
3. **Install Dependencies**: `npm install`
4. **Run the Development Server**: `npm start`

### Setting Up the Agent Architecture

1. **Install Node.js and npm**: Ensure you have Node.js and npm installed on your machine.
2. **Navigate to Agent Directory**: `cd masterchef/agent`
3. **Install Dependencies**: `npm install`
4. **Deploy to Cloudflare Workers**: Follow the Cloudflare Workers documentation to deploy the agent code.

### Deployment Instructions

#### Linode Server

1. **Create a Linode Account**: Sign up for a Linode account.
2. **Set Up a Linode Server**: Create a new Linode server with the recommended specifications.
3. **Install Docker**: Follow the Docker installation guide for your server's operating system.
4. **Clone the Repository**: `git clone https://github.com/raeeceip/masterchef.git`
5. **Navigate to Project Directory**: `cd masterchef`
6. **Run Docker Compose**: `docker-compose up -d`

#### Cloudflare Integration

1. **Create a Cloudflare Account**: Sign up for a Cloudflare account.
2. **Set Up Cloudflare Workers**: Follow the Cloudflare Workers documentation to set up your environment.
3. **Deploy Frontend to Cloudflare Pages**: Follow the Cloudflare Pages documentation to deploy the frontend application.
4. **Configure Workers KV**: Set up Workers KV for agent state storage.
5. **Secure Administration**: Use Cloudflare Access to secure the administration interface.

### Running Benchmarks and Analyzing Results

1. **Create a Benchmark Session**: Use the frontend application to create a new benchmark session.
2. **Upload Model**: Upload the LLM model through the model uploading interface.
3. **Configure Scenario**: Set up the scenario configuration for the benchmark.
4. **Execute Scenario**: Run the scenario and monitor the progress through the frontend application.
5. **Analyze Results**: Use the evaluation dashboards to analyze the results and export the data for further analysis.
