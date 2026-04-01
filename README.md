# MCP KG Inquirer

MCP client for Knowledge Graph Engine integration.

## Overview

`mcp_kg_inquirer` is a Python client for interacting with the Knowledge Graph Engine via the Model Context Protocol (MCP). It provides:

- **Search Operations**: Vector, text2cypher, vector_cypher, and hybrid search modes
- **RAG Queries**: Retrieval-Augmented Generation for question answering
- **Direct HTTP Transport**: Simple GraphQL requests with retry logic
- **Circuit Breaker**: Resilience pattern to prevent cascading failures

## Installation

```bash
pip install mcp_kg_inquirer
```

## Dependencies

- **pydantic** (>=2.0.0) - Data validation
- **python-dotenv** (>=1.0.0) - Environment variable loading

## Quick Start

```python
import asyncio
import logging
from mcp_kg_inquirer import MCPKGInquirer

async def main():
    # Create client with API key
    client = MCPKGInquirer(
        logging.getLogger(__name__),
        endpoint_id="my-endpoint",
        part_id="my-partition",
        api_key="my-api-key",
    )
    
    # Or create client with bearer token (preferred for OAuth/JWT)
    client = MCPKGInquirer(
        logging.getLogger(__name__),
        endpoint_id="my-endpoint",
        part_id="my-partition",
        bearer_token="my-jwt-token",
    )
    
    # Search using vector similarity
    results = await client.search_vector("machine learning", limit=10)
    print(f"Found {results.total} results")
    for result in results.results:
        print(f"  [{result.score:.2f}] {result.content[:100]}...")
    
    # Search using hybrid mode
    results = await client.search_hybrid("neural networks")
    
    # RAG query
    answer = await client.rag("What is machine learning?")
    print(f"Answer: {answer.answer}")
    print(f"Context: {len(answer.context)} documents")
    
    # Close client
    await client.close()

asyncio.run(main())
```

## Configuration

### Authentication

The client supports two authentication methods:

#### Option 1: API Key
```python
import logging

client = MCPKGInquirer(
    logging.getLogger(__name__),
    endpoint_id="my-endpoint",
    part_id="my-partition",
    api_key="my-api-key",
)
```

#### Option 2: Bearer Token (OAuth/JWT)
```python
import logging

client = MCPKGInquirer(
    logging.getLogger(__name__),
    endpoint_id="my-endpoint",
    part_id="my-partition",
    bearer_token="my-jwt-token",
)
```

### Environment Variables

```bash
# Required
export KGE_ENDPOINT_ID="my-endpoint"
export KGE_PART_ID="my-partition"

# Authentication (provide ONE)
export KGE_API_KEY="my-api-key"          # Option 1: API key
export KGE_BEARER_TOKEN="my-jwt-token"   # Option 2: Bearer token (preferred)

# Optional
export KGE_BASE_URL="http://localhost:8000"
export KGE_TIMEOUT="30.0"
export KGE_MAX_RETRIES="3"
```

### From Environment

```python
import logging

from mcp_kg_inquirer import MCPKGInquirer

client = MCPKGInquirer.from_env(logging.getLogger(__name__))
```

## Usage

### Search

```python
# Basic search
results = await client.search("machine learning")

# Vector search (semantic similarity)
results = await client.search_vector("neural networks")

# Hybrid search (vector + fulltext)
results = await client.search_hybrid("deep learning")

# Search with filters
results = await client.search(
    "AI",
    data_type="article",
    filters={"category": "technology"},
    page=1,
    limit=20,
)

# Text-to-Cypher search (LLM-generated Cypher)
results = await client.search(
    "find products with price > 100",
    search_mode="text2cypher",
)

# Vector-Cypher search (vector + custom traversal)
results = await client.search(
    "machine learning algorithms",
    search_mode="vector_cypher",
    prompt="Focus on algorithmic complexity",
)
```

### RAG

```python
# Basic RAG
answer = await client.rag("What is deep learning?")

# With custom prompt
answer = await client.rag(
    "Explain neural networks",
    prompt="You are a technical assistant. Be concise.",
)

# With use case (predefined prompts)
answer = await client.rag(
    "Summarize AI",
    use_case="summary",  # Options: default, summary, explanation
)
```

### Async Context Manager

```python
import logging

async with MCPKGInquirer.from_env(logging.getLogger(__name__)) as client:
    results = await client.search("test")
    # Client automatically closed
```

## Search Modes

| Mode | Description | Best For |
|------|-------------|----------|
| `vector` | Semantic similarity using embeddings | Natural language queries |
| `text2cypher` | LLM-generated Cypher queries | Structured queries |
| `vector_cypher` | Vector + custom traversal | Complex graph patterns |
| `hybrid` | Vector + fulltext combined | Mixed search needs |

## API Reference

### MCPKGInquirer

```python
class MCPKGInquirer:
    def __init__(
        self,
        logger: logging.Logger,
        **setting: dict[str, Any],
    ): ...
    
    async def search(
        self,
        query_text: str,
        data_type: str = None,
        filters: dict = None,
        similarity_search: bool = False,
        relevance_search: bool = False,
        page: int = 1,
        limit: int = 10,
        prompt: str = None,
        search_mode: str = None,
    ) -> SearchResponse: ...
    
    async def search_vector(
        self,
        query_text: str,
        data_type: str = None,
        filters: dict = None,
        page: int = 1,
        limit: int = 10,
    ) -> SearchResponse: ...
    
    async def search_hybrid(
        self,
        query_text: str,
        data_type: str = None,
        filters: dict = None,
        page: int = 1,
        limit: int = 10,
    ) -> SearchResponse: ...
    
    async def rag(
        self,
        query_text: str,
        prompt: str = None,
        use_case: str = None,
    ) -> RAGResponse: ...
    
    async def close() -> None: ...
```

### SearchResponse

```python
@dataclass
class SearchResponse:
    results: List[SearchResult]
    total: int
    page: int
    limit: int

@dataclass
class SearchResult:
    content: str
    score: float
    metadata: dict
    node_id: str
    labels: List[str]
```

### RAGResponse

```python
@dataclass
class RAGResponse:
    answer: str
    context: List[RAGContext]
    model: str
    latency_ms: float

@dataclass
class RAGContext:
    content: str
    score: float
    metadata: dict
    source: str
```

## Error Handling

```python
from mcp_kg_inquirer.exceptions import (
    MCPKGInquirerError,
    ConnectionError,
    AuthenticationError,
    SearchError,
    RAGError,
    ValidationError,
    TimeoutError,
    RateLimitError,
)

try:
    results = await client.search("test")
except ValidationError as e:
    print(f"Invalid parameters: {e}")
except ConnectionError as e:
    print(f"Connection failed: {e}")
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
except SearchError as e:
    print(f"Search failed: {e}")
```

## Development

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Run Tests with Coverage

```bash
pytest --cov=mcp_kg_inquirer --cov-report=html
```

### Type Checking

```bash
mypy mcp_kg_inquirer
```

### Linting

```bash
ruff check mcp_kg_inquirer
```

## Architecture

```
mcp_kg_inquirer/
├── __init__.py      # Public API
├── client.py        # Main client class
├── config.py        # Configuration management
├── connection.py   # HTTP connection pooling
├── exceptions.py    # Custom exceptions
├── search.py        # Search implementation
├── rag.py           # RAG implementation
└── utils.py         # Helper functions
```

## Backend Integration

The client integrates with the `knowledge_graph_engine` backend:

```
┌─────────────────┐      HTTP/GraphQL      ┌─────────────────┐
│  mcp_kg_inquirer │ ───────────────────── │ knowledge_graph │
│     (Client)     │                       │     Engine      │
└─────────────────┘                       └─────────────────┘
                                                  │
                                                  │ Neo4j Driver
                                                  ▼
                                          ┌─────────────────┐
                                          │    Neo4j DB     │
                                          │  (Vector + Graph)│
                                          └─────────────────┘
```

## License

MIT License
