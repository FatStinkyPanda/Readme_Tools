# Quick Start Guide

Get started with README Tools in minutes!

## Prerequisites

- Python 3.11 or higher
- Git
- An API key from OpenAI, Anthropic, or local Ollama installation

## Installation

1. **Clone the repository**
```bash
git clone https://github.com/FatStinkyPanda/Readme_Tools
cd Readme_Tools
```

2. **Create virtual environment**
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

## Configuration

1. **Copy environment template**
```bash
cp .env.example .env
```

2. **Edit `.env` and add your API key**
```env
# For OpenAI
OPENAI_API_KEY=sk-...
DEFAULT_AI_PROVIDER=openai
DEFAULT_MODEL=gpt-4-turbo

# Or for Anthropic
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_AI_PROVIDER=anthropic
DEFAULT_MODEL=claude-3-sonnet-20240229

# Or for local Ollama
DEFAULT_AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

## Usage

### Option 1: Python API (Programmatic)

```python
import asyncio
from readme_organizer.core.parser import Parser
from readme_organizer.core.storage import Storage
from readme_organizer.core.categorizer import Categorizer
from readme_organizer.core.indexer import Indexer
from readme_organizer.ai_providers.factory import get_ai_adapter

async def index_readme():
    # Initialize components
    storage = Storage("data/readme_tools.db")
    await storage.connect()

    # Parse README
    parser = Parser()
    sections = await parser.parse_file("README.md")

    # Set up AI
    ai_adapter = get_ai_adapter(
        provider="openai",
        api_key="your-key",
        model="gpt-4-turbo"
    )

    # Index
    categorizer = Categorizer(ai_adapter)
    indexer = Indexer(storage, categorizer)
    stats = await indexer.index_readme(sections)

    print(f"Indexed {stats['sections_indexed']} sections!")
    await storage.close()

asyncio.run(index_readme())
```

### Option 2: REST API

1. **Start the API server**
```bash
uvicorn api.main:app --reload
```

2. **Visit the interactive docs**
Open http://localhost:8000/docs in your browser

3. **Parse a README**
```bash
curl -X POST "http://localhost:8000/api/v1/readme/parse" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "README.md",
    "ai_provider": "openai",
    "model": "gpt-4-turbo"
  }'
```

4. **Search for content**
```bash
curl "http://localhost:8000/api/v1/search?q=installation&limit=5"
```

5. **Get context for AI agents**
```bash
curl -X POST "http://localhost:8000/api/v1/context/request" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I install this?",
    "max_tokens": 2000
  }'
```

### Option 3: Example Script

Run the included example:
```bash
python example_usage.py
```

## Common Tasks

### Index Your Project's README

```python
from readme_organizer import index_readme_file

stats = await index_readme_file(
    "path/to/README.md",
    ai_provider="openai",
    api_key="your-key"
)
```

### Search Documentation

```python
from readme_organizer.core.search import SearchEngine

search = SearchEngine(storage)
results = await search.search("installation guide", limit=5)

for result in results["results"]:
    print(f"{result['title']}: {result['snippet']}")
```

### Provide Context to AI Agents

```python
from readme_organizer.core.context_provider import ContextProvider

provider = ContextProvider(storage, search_engine)
context = await provider.get_context(
    query="How do I configure the database?",
    max_tokens=2000
)

# Use context['context'] with your AI agent
print(context['context'])
```

## Next Steps

- Read the full [README](README.md) for detailed documentation
- Check out the [Architecture](ARCHITECTURE.md) to understand the system
- Explore the [API docs](http://localhost:8000/docs) (after starting the server)
- See example implementations in `example_usage.py`

## Troubleshooting

### "Database not connected" error
Make sure to call `await storage.connect()` before using storage methods.

### "No API key provided" error
Ensure your `.env` file has the correct API key for your chosen provider.

### Import errors
Make sure you've activated the virtual environment and installed all dependencies:
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### AI provider not working
- **OpenAI**: Verify your API key at https://platform.openai.com/api-keys
- **Anthropic**: Verify your API key at https://console.anthropic.com/
- **Ollama**: Make sure Ollama is running (`ollama serve`)

## Support

- GitHub Issues: https://github.com/FatStinkyPanda/Readme_Tools/issues
- Documentation: See README.md and ARCHITECTURE.md

Happy documenting! 📚
