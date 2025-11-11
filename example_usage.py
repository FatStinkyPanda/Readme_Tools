"""Example usage of README Tools.

This script demonstrates how to use the README organizer programmatically.
"""

import asyncio
from pathlib import Path

from config import get_settings
from readme_organizer.ai_providers.factory import get_ai_adapter
from readme_organizer.core.categorizer import Categorizer
from readme_organizer.core.context_provider import ContextProvider
from readme_organizer.core.indexer import Indexer
from readme_organizer.core.parser import Parser
from readme_organizer.core.search import SearchEngine
from readme_organizer.core.storage import Storage


async def main():
    """Main example function."""
    print("=" * 60)
    print("README Tools - Example Usage")
    print("=" * 60)

    # Get settings
    settings = get_settings()
    settings.ensure_data_directory()

    # Initialize storage
    print("\n1. Initializing storage...")
    storage = Storage(settings.database_path)
    await storage.connect()
    print("   ✓ Storage connected")

    # Clear existing data for demo
    await storage.clear_all()
    print("   ✓ Cleared existing data")

    # Parse README
    print("\n2. Parsing README file...")
    parser = Parser()

    readme_path = Path("README.md")
    if not readme_path.exists():
        print("   ✗ README.md not found. Using example content...")
        example_content = """# Example Project

## Installation

To install the project, run:

```bash
pip install example-project
```

## Configuration

Create a `.env` file with the following:

```
API_KEY=your_key_here
DATABASE_URL=sqlite:///db.sqlite
```

## Usage

Basic usage example:

```python
from example import Client

client = Client(api_key="your_key")
result = client.process_data()
```

## API Reference

### Client Class

The main client class for interacting with the API.

Methods:
- `process_data()` - Process data
- `get_results()` - Get results

## Testing

Run tests with:

```bash
pytest tests/
```

## Contributing

We welcome contributions! Please see CONTRIBUTING.md for details.
"""
        sections = await parser.parse_content(example_content)
    else:
        sections = await parser.parse_file(readme_path)

    print(f"   ✓ Parsed {len(sections)} top-level sections")

    # Initialize AI adapter
    print("\n3. Initializing AI adapter...")
    ai_adapter = get_ai_adapter(
        provider=settings.default_ai_provider,
        api_key=(
            settings.openai_api_key
            if settings.default_ai_provider == "openai"
            else settings.anthropic_api_key
        ),
        model=settings.default_model,
    )
    print(f"   ✓ Using {settings.default_ai_provider} provider")

    # Index README
    print("\n4. Indexing README with AI categorization...")
    categorizer = Categorizer(ai_adapter)
    indexer = Indexer(storage, categorizer)

    stats = await indexer.index_readme(sections)
    print(f"   ✓ Indexed {stats['sections_indexed']} sections")
    print(f"   ✓ Created {len(stats['categories_created'])} categories")
    print(f"   ✓ Extracted {stats['total_keywords']} keywords")
    print(f"   ✓ Generated {stats['total_tags']} tags")

    # Search examples
    print("\n5. Search examples...")
    search_engine = SearchEngine(storage)

    # Full-text search
    print("\n   a) Full-text search for 'installation':")
    results = await search_engine.search("installation", limit=3)
    for i, result in enumerate(results["results"], 1):
        print(f"      {i}. {result['title']}")
        print(f"         Category: {result['category']}")

    # Keyword search
    print("\n   b) Search by keywords:")
    all_keywords = await search_engine.get_all_keywords()
    top_keywords = list(all_keywords.keys())[:3]
    print(f"      Top keywords: {', '.join(top_keywords)}")

    if top_keywords:
        keyword_results = await search_engine.search_by_keywords(top_keywords[:2], limit=3)
        for i, result in enumerate(keyword_results, 1):
            print(f"      {i}. {result['title']}")

    # Tag search
    print("\n   c) Search by tags:")
    all_tags = await search_engine.get_all_tags()
    print(f"      Available tags: {', '.join(list(all_tags.keys())[:5])}")

    # Context for AI agents
    print("\n6. Context provision for AI agents...")
    context_provider = ContextProvider(storage, search_engine, max_tokens=2000)

    context = await context_provider.get_context(
        query="How do I install and configure this project?",
        max_tokens=2000,
        include_related=True,
    )

    print(f"   Query: {context['query']}")
    print(f"   Sections included: {context['sections_included']}")
    print(f"   Token estimate: {context['token_estimate']}")
    print("\n   Context preview:")
    print("   " + "-" * 56)
    preview = context["context"][:500]
    print("   " + preview.replace("\n", "\n   "))
    if len(context["context"]) > 500:
        print("   ... (truncated)")
    print("   " + "-" * 56)

    # Get summary
    print("\n7. Summary of indexed content...")
    summary = await context_provider.get_summary()
    print(f"   Total categories: {summary['total_categories']}")
    print(f"   Categories: {', '.join(summary['categories'])}")
    print(f"   Total keywords: {summary['total_keywords']}")
    print(f"   Total tags: {summary['total_tags']}")

    # Cleanup
    await storage.close()

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)
    print("\nTo use the API:")
    print("  uvicorn api.main:app --reload")
    print("  Then visit: http://localhost:8000/docs")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
