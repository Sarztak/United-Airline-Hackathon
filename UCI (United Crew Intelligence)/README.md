# UCI MVP - United Crew Intelligence

🚀 **A Multi-Agent System for Crew Disruption and Recovery**

Built for the United Airlines Hackathon, UCI MVP demonstrates an intelligent multi-agent system that monitors, plans, and reassigns disrupted crew in real-time using AI, RAG (Retrieval-Augmented Generation), and sophisticated orchestration.

## 🎯 Overview

UCI MVP is a sophisticated airline operations management system that uses multiple specialized AI agents to handle flight disruptions automatically. The system combines rule-based logic, semantic search over airline policies, and LLM-powered decision making to provide comprehensive disruption resolution.

### Key Features

- **Real-time Crew Monitoring**: Continuously monitors crew duty status and legality
- **Intelligent Crew Planning**: Automatically finds spare crew and repositioning options
- **Dynamic Crew Reassignment**: Makes real-time crew assignment decisions during disruptions
- **Multi-Agent Architecture**: Specialized agents for crew assignment, operations support, and policy reasoning
- **RAG-Powered Policy Engine**: Semantic search over airline policies using sentence transformers
- **LLM Integration**: OpenAI GPT-4 for complex policy reasoning and escalations
- **Real-time Web Dashboard**: Live monitoring of agent decisions and crew status
- **Comprehensive Logging**: Structured logging showing agent reasoning and decisions

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │   CLI Interface │    │   API Endpoints │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │      Orchestrator         │
                    └─────────────┬─────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
┌───────▼────────┐    ┌──────────▼──────────┐    ┌─────────▼─────────┐
│ Crew Assignment│    │  Operations Support │    │   Policy Agent    │
│     Agent      │    │      Agent          │    │   (LLM + RAG)     │
└────────────────┘    └─────────────────────┘    └───────────────────┘
        │                         │                         │
        │                         │                         │
┌───────▼────────┐    ┌──────────▼──────────┐    ┌─────────▼─────────┐
│  Crew Tools    │    │   Hotel Booking     │    │  Policy Database  │
│• Query Roster  │    │   Ground Support    │    │• RAG Retrieval    │
│• Find Spares   │    │   Transportation    │    │• Confidence Score │
│• Check Legality│    │                     │    │• Fallback Policies│
└────────────────┘    └─────────────────────┘    └───────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key (optional, system works with mock responses)
- Git

### Installation

1. **Clone the repository**
   ```bash
   cd /path/to/your/workspace
   git clone <repository-url>
   cd iocca_mvp
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.template .env
   # Edit .env with your OpenAI API key and other settings
   ```

### Running the System

#### Option 1: Web Interface (Recommended)
```bash
python web/app.py
```
Then open http://localhost:8000 in your browser.

#### Option 2: Command Line Interface
```bash
python main.py
```

#### Option 3: API Server
```bash
uvicorn web.app:app --host 0.0.0.0 --port 8000 --reload
```

## 🎮 Usage

### Web Dashboard

The web dashboard provides a real-time interface for:

- **Disruption Simulation**: Click "Simulate Disruption" to test the system
- **Live Monitoring**: View active requests and system status
- **Agent Status**: Monitor individual agent health
- **Configuration**: View system configuration
- **Policy Browser**: Browse available airline policies
- **Live Logs**: Real-time system logging

### API Endpoints

- `GET /api/health` - System health check
- `POST /api/disruption/simulate` - Simulate a disruption
- `GET /api/disruption/{id}` - Get disruption status
- `POST /api/crew-assignment` - Direct crew assignment request
- `POST /api/ops-support` - Direct operations support request
- `GET /api/policies` - List available policies
- `GET /api/config` - Get system configuration

### CLI Commands

```bash
# Run basic simulation
python main.py

# Run with specific configuration
LOG_LEVEL=DEBUG python main.py

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

## 🔧 Configuration

Configuration is managed through environment variables and the `config.py` module:

### Environment Variables

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=256
OPENAI_TEMPERATURE=0.2

# RAG Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
CONFIDENCE_THRESHOLD=0.55

# Application Configuration
DEBUG=False
MAX_WORKERS=4
TIMEOUT_SECONDS=30
HOST=0.0.0.0
PORT=8000

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/iocca.log
```

## 🤖 Agents

### 1. Crew Assignment Agent
**Purpose**: Manages crew scheduling and assignment decisions

**Capabilities**:
- Check crew duty time legality
- Find available spare crew members
- Initiate crew repositioning
- Apply crew scheduling policies

**Input**: Flight ID, crew roster, flight schedule, repositioning options, duty rules
**Output**: Assignment decision, spare crew usage, policy recommendations

### 2. Operations Support Agent
**Purpose**: Handles operational logistics and support tasks

**Capabilities**:
- Hotel booking for stranded crew
- Ground transportation coordination
- Crew accommodation management
- Cost optimization

**Input**: Crew ID, location, hotel inventory
**Output**: Booking confirmations, support arrangements, cost information

### 3. Policy Agent (LLM + RAG)
**Purpose**: Provides intelligent policy reasoning and escalation decisions

**Capabilities**:
- Semantic search over policy documents
- GPT-4 powered complex reasoning
- Escalation decision making
- Policy compliance checking

**Input**: Complex scenarios, policy queries, escalation requests
**Output**: Policy recommendations, escalation decisions, reasoning explanations

## 📊 Data Models

The system uses Pydantic models for data validation:

- **CrewMember**: Crew information and status
- **Flight**: Flight schedule and status information
- **Hotel**: Hotel inventory and availability
- **RepositioningFlight**: Crew repositioning options
- **DutyRules**: Regulatory compliance rules
- **Disruption**: Disruption event information

See `models/schemas.py` for complete model definitions.

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration

# Run with verbose output
pytest -v
```

### Test Structure

```
tests/
├── __init__.py
├── test_config.py          # Configuration tests
├── test_models.py          # Data model tests
├── test_policy_retriever.py # RAG system tests
├── test_agents.py          # Agent functionality tests
└── test_web_api.py         # API endpoint tests
```

## 📝 Logging

The system implements comprehensive structured logging:

### Log Levels
- **DEBUG**: Detailed diagnostic information
- **INFO**: General operational information
- **WARNING**: Important events that might need attention
- **ERROR**: Error conditions that don't stop the application
- **CRITICAL**: Serious errors that might stop the application

### Log Formats
- **JSON**: Structured logs for production systems
- **Console**: Human-readable logs for development

### Agent-Specific Logging
Each agent has specialized logging for:
- Task initiation and completion
- Performance metrics
- Policy retrievals
- LLM API calls
- Error conditions

## 🔍 Monitoring

### Health Checks
- System health endpoint: `/api/health`
- Agent status monitoring
- Configuration validation
- External API connectivity

### Metrics
- Request processing times
- Agent success rates
- Policy retrieval confidence scores
- LLM token usage
- Error rates and types

## 🛠️ Development

### Project Structure

```
iocca_mvp/
├── agents/                 # AI agents
│   ├── crew_assignment.py
│   ├── ops_support.py
│   └── policy_agent_llm.py
├── config.py              # Configuration management
├── data/                  # Sample data
├── main.py               # CLI entry point
├── models/               # Data models
│   ├── __init__.py
│   └── schemas.py
├── orchestrator/         # Agent orchestration
│   └── orchestrator.py
├── policies/            # Policy engine
│   ├── policy_docs.json
│   └── rag_policy_retriever.py
├── tests/              # Unit tests
├── tools/              # Utility functions
├── utils/              # Common utilities
│   ├── __init__.py
│   ├── exceptions.py
│   └── logger.py
└── web/                # Web interface
    ├── app.py
    └── templates/
        └── dashboard.html
```

### Adding New Agents

1. Create agent module in `agents/`
2. Implement agent interface
3. Add to orchestrator
4. Update web API endpoints
5. Add tests
6. Update documentation

### Adding New Policies

1. Add policy to `policies/policy_docs.json`
2. Test policy retrieval
3. Verify confidence scoring
4. Update policy documentation

## 🚀 Deployment

### Production Deployment

```bash
# Install production dependencies
pip install -r requirements.txt

# Set production environment variables
export DEBUG=False
export LOG_LEVEL=INFO
export OPENAI_API_KEY=your_production_key

# Run with production server
uvicorn web.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit a pull request

### Code Style
- Use Black for code formatting
- Follow PEP 8 guidelines
- Add type hints
- Include docstrings
- Write tests for new features

## 📈 Performance

### Benchmarks
- Average disruption processing: <5 seconds
- Policy retrieval: <200ms
- LLM response time: 1-3 seconds
- Web dashboard load time: <1 second

### Optimization Tips
- Use async operations for I/O bound tasks
- Cache policy embeddings
- Implement request batching
- Monitor memory usage
- Profile agent performance

## 🐛 Troubleshooting

### Common Issues

1. **OpenAI API Key Not Set**
   - System will use mock responses
   - Set `OPENAI_API_KEY` environment variable

2. **Policy Loading Errors**
   - Check `policies/policy_docs.json` exists
   - Verify JSON format is valid

3. **Web Interface Not Loading**
   - Check if port 8000 is available
   - Verify all dependencies installed

4. **Import Errors**
   - Ensure virtual environment is activated
   - Install all requirements

### Debug Mode

```bash
DEBUG=True LOG_LEVEL=DEBUG python main.py
```

## 📋 Roadmap

### Short Term
- [ ] Add more agent types
- [ ] Implement agent-to-agent communication
- [ ] Add more policy documents
- [ ] Improve web dashboard UX

### Medium Term
- [ ] Add machine learning models
- [ ] Implement predictive analytics
- [ ] Add real-time data feeds
- [ ] Create mobile interface

### Long Term
- [ ] Multi-airline support
- [ ] Advanced optimization algorithms
- [ ] Integration with airline systems
- [ ] Regulatory compliance automation

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- United Airlines for the hackathon opportunity
- OpenAI for GPT-4 API
- Hugging Face for sentence transformers
- FastAPI and Pydantic communities

## 📞 Support

For questions, issues, or contributions:
- Create an issue on GitHub
- Contact the development team
- Check the troubleshooting section

---

**Built with ❤️ for the United Airlines Hackathon**