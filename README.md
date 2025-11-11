# README Tools

**For using "README.md" as a single source of truth for project development.**

Particularly helpful when using AI agents. Contains several tools and services for README file planning, design, architecture, development, and integration strategies and methods.

**Recommended use with "OpenMemory-Code".**

## Overview

README Tools is a suite of intelligent tools designed to help developers and AI agents work with large, complex README.md files. Instead of dealing with massive documentation files that are hard to navigate and too large for AI context windows, README Tools breaks them down into organized, searchable, and discoverable parts.

## Features

### README Organizer & Discovery Tool

The first and primary tool in the suite:

- **Intelligent Categorization**: AI-powered parsing that understands your README structure and content
- **Smart Indexing**: Full-text search with SQLite FTS5, keyword extraction, and tagging
- **Section Discovery**: Find relevant documentation sections quickly with powerful search
- **AI Agent Integration**: Optimized for providing context to AI agents with intelligent section delivery
- **RESTful API**: Comprehensive API endpoints for programmatic access
- **Multi-Provider AI**: Support for OpenAI, Anthropic Claude, and local Ollama models

### Key Capabilities

1. **Break Down Large READMEs**: Automatically parse and split large README files into manageable, categorized parts
2. **Intelligent Indexing**: Extract keywords, generate tags, and create searchable indices automatically
3. **Advanced Search**: Full-text search, keyword filtering, tag-based discovery, and section extraction
4. **Context for AI Agents**: Provide relevant README sections to AI agents without overwhelming their context windows
5. **Extensible Architecture**: Built to support multiple tools in the suite with a common API framework

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system design.

### Technology Stack

- **Python 3.11+** - Modern Python with async support
- **FastAPI** - High-performance API framework with auto-generated docs
- **SQLite FTS5** - Lightweight full-text search
- **Multi-AI Provider** - OpenAI GPT-4, Anthropic Claude, or local Ollama

### Project Structure

```
Readme_Tools/
├── readme_organizer/          # Main README organizer tool
│   ├── core/                  # Core functionality
│   │   ├── parser.py         # Markdown parsing
│   │   ├── categorizer.py    # AI-powered categorization
│   │   ├── storage.py        # SQLite database layer
│   │   ├── indexer.py        # Indexing and tagging
│   │   ├── search.py         # Search engine
│   │   └── context_provider.py # AI agent context delivery
│   ├── ai_providers/          # AI provider adapters
│   │   ├── base_adapter.py   # Common interface
│   │   ├── openai_adapter.py # OpenAI integration
│   │   ├── anthropic_adapter.py # Anthropic integration
│   │   └── ollama_adapter.py # Local Ollama integration
│   └── utils/                 # Utility functions
├── api/                       # FastAPI application
│   ├── main.py               # API entry point
│   ├── routes/               # API route handlers
│   └── models.py             # Pydantic models
├── config/                    # Configuration files
│   ├── settings.py           # Application settings
│   └── ai_config.yaml        # AI provider configs
├── tests/                     # Test suite
├── data/                      # Data storage (SQLite DBs)
└── docs/                      # Additional documentation

[Future Tools]
├── readme_validator/          # Validate README completeness
├── readme_generator/          # Generate README from code
└── ai_tool_use/              # AI agent tool use system
```

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/FatStinkyPanda/Readme_Tools
cd Readme_Tools

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Copy the example configuration:
```bash
cp config/ai_config.example.yaml config/ai_config.yaml
```

2. Add your AI provider API keys to `config/ai_config.yaml`

### Running the API

```bash
# Development mode with auto-reload
uvicorn api.main:app --reload

# Production mode
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`
Interactive API docs at `http://localhost:8000/docs`

## Usage

### Parse and Organize a README

```bash
curl -X POST "http://localhost:8000/api/v1/readme/parse" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "path/to/README.md",
    "options": {
      "ai_provider": "openai",
      "model": "gpt-4-turbo"
    }
  }'
```

### Search for Content

```bash
# Full-text search
curl "http://localhost:8000/api/v1/search?q=installation&limit=5"

# Search by keywords
curl "http://localhost:8000/api/v1/search/keywords?keywords=api,configuration"

# Search by tags
curl "http://localhost:8000/api/v1/search/tags?tags=setup,deployment"
```

### Get Context for AI Agents

```bash
curl -X POST "http://localhost:8000/api/v1/context/request" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "How do I set up the database?",
    "max_tokens": 2000,
    "include_related": true
  }'
```

## API Documentation

Full API documentation is available at `/docs` when running the server (Swagger UI) or `/redoc` (ReDoc).

### Key Endpoints

- `POST /api/v1/readme/parse` - Parse and organize a README file
- `GET /api/v1/readme/parts` - List all README parts
- `GET /api/v1/readme/parts/{id}` - Get a specific part
- `GET /api/v1/search` - Full-text search across all parts
- `GET /api/v1/search/keywords` - Search by keywords
- `GET /api/v1/search/tags` - Search by tags
- `POST /api/v1/context/request` - Request relevant context for AI agents
- `GET /api/v1/categories` - List all categories
- `GET /api/v1/stats` - Get statistics about indexed content

## Integration with AI Agents

README Tools is designed to work seamlessly with AI agents. The context provider intelligently selects relevant sections based on:

1. **Relevance scoring** - Matches your query against indexed content
2. **Token management** - Respects context window limits
3. **Progressive loading** - Delivers most relevant content first
4. **Related content** - Includes related sections for better understanding

### Example: OpenAI Function Calling

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_readme",
            "description": "Search the project README for relevant information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        }
    }
]
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Format code
black readme_organizer/ api/ tests/

# Lint
ruff check readme_organizer/ api/ tests/

# Type checking
mypy readme_organizer/ api/
```

## Roadmap

- [x] Architecture design
- [ ] Core README parser
- [ ] AI-powered categorization
- [ ] SQLite FTS5 indexing
- [ ] FastAPI endpoints
- [ ] Multi-provider AI support
- [ ] Context provider for AI agents
- [ ] Comprehensive test suite
- [ ] Documentation and examples
- [ ] Docker deployment
- [ ] Vector embeddings for semantic search
- [ ] Real-time README sync
- [ ] Web dashboard UI

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## License

MIT License - see LICENSE file for details

## Related Projects

- **OpenMemory-Code**: AI agent memory system for code projects (recommended companion tool)

## Support

For issues, questions, or contributions, please visit:
https://github.com/FatStinkyPanda/Readme_Tools/issues
