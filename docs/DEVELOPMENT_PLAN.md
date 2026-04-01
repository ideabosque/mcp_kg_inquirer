# Knowledge Graph MCP Integration - Development Plan

## Executive Summary

This document outlines the development plan for integrating `mcp_kg_engine` (MCP client) with `knowledge_graph_engine` (backend) to provide unified search and RAG (Retrieval-Augmented Generation) capabilities via the Model Context Protocol (MCP).

**Last Updated**: 2026-03-31
**Current Status**: Planning Phase
**Project Scope**: MCP Tool Integration for Knowledge Graph Operations

---

## 1. Project Overview

### 1.1 Objectives

- **Integrate MCP Tools**: Enable MCP clients to interact with `knowledge_graph_engine` for:
  - **Search Operations**: Vector, text2cypher, vector_cypher, and hybrid search modes
  - **RAG Queries**: Context-aware question answering using GraphRAG

- **Maintain GraphQL API**: Preserve existing GraphQL endpoints while adding MCP interface
- **Unified Backend**: Single `knowledge_graph_engine` serving both GraphQL and MCP clients
- **Scalability**: Support multi-tenant operations with partition-based isolation

### 1.2 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Client Layer                         │
│                     (mcp_kg_engine)                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐  ┌─────────────────────────┐      │
│  │      MCP Tool:          │  │      MCP Tool:          │      │
│  │        search           │  │         rag             │      │
│  └───────────┬─────────────┘  └───────────┬─────────────┘      │
│              │                             │                    │
│              └──────────────┬───────────────┘                    │
│                             │                                   │
└─────────────────────────────┼───────────────────────────────────┘
                              │ HTTP/GraphQL
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Knowledge Graph Engine                      │
│                  (knowledge_graph_engine)                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐  ┌─────────────────────────┐      │
│  │       Search            │  │         RAG             │      │
│  │       Handler           │  │       Handler           │      │
│  └───────────┬─────────────┘  └───────────┬─────────────┘      │
│              │                             │                    │
│              └──────────────┬───────────────┘                    │
│                             │                                   │
│  ┌───────────────────────┴───────────────────────────────────┐ │
│  │                  GraphRAG Util (Neo4j)                    │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │ │
│  │  │  Vector  │  │ Text2Cyp │  │ VectorCy │  │  Hybrid  │ │ │
│  │  │  Search  │  │   her    │  │   pher   │  │  Search  │ │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Neo4j Database                          │
│              (Vector Index + Fulltext Index + Graph)           │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Technology Stack

| Component | Technology |
|-----------|-----------|
| **MCP Protocol** | Model Context Protocol |
| **MCP Client** | mcp_kg_engine |
| **Backend** | knowledge_graph_engine (FastAPI + GraphQL) |
| **Graph Database** | Neo4j 5.x |
| **Vector Search** | Neo4j Vector Index |
| **LLM** | OpenAI GPT-4o / Anthropic Claude / Ollama |
| **Embeddings** | OpenAI text-embedding-3-small |
| **GraphRAG** | neo4j-graphrag-python |
| **Python** | 3.11+ |

---

## 2. MCP Tools Integration

### 2.1 Tool: `search`

**Purpose**: Search the knowledge graph using multiple strategies

**Input Schema**:
```json
{
  "query_text": "string (required)",
  "data_type": "string (optional)",
  "filters": "object (optional)",
  "similarity_search": "boolean (optional)",
  "relevance_search": "boolean (optional)",
  "page": "integer (optional, default: 1)",
  "limit": "integer (optional, default: 10)",
  "prompt": "string (optional)"
}
```

**Implementation Mapping**:
| MCP Parameter | GraphQL Parameter | Search Mode |
|-------------|-------------------|-------------|
| `query_text` | `queryText` | All modes |
| `similarity_search=true` | `searchMode: "vector"` | Vector Search |
| `relevance_search=true` | `searchMode: "hybrid"` | Hybrid Search |
| `filters` | `filters` | Applied to all modes |
| `page`, `limit` | `page`, `limit` | Pagination |

**Backend Implementation**:
- Entry Point: `knowledge_graph_engine/queries/search.py:resolve_search()`
- Handler: `knowledge_graph_engine/handlers/search_handler.py:SearchHandler.search()`
- Supported Modes:
  - `vector`: Semantic similarity using embeddings
  - `text2cypher`: LLM-generated Cypher queries
  - `vector_cypher`: Vector + custom traversal
  - `hybrid`: Vector + fulltext combined

**Response Format**:
```json
{
  "results": [...],
  "total": 42,
  "page": 1,
  "limit": 10
}
```

### 2.2 Tool: `rag`

**Purpose**: Perform Retrieval-Augmented Generation for Q&A

**Input Schema**:
```json
{
  "query_text": "string (required)",
  "prompt": "string (optional)"
}
```

**Implementation Mapping**:
| MCP Parameter | GraphQL Parameter | Description |
|-------------|-------------------|-------------|
| `query_text` | `queryText` | The question to answer |
| `prompt` | `prompt` | Custom system prompt template |

**Backend Implementation**:
- Entry Point: `knowledge_graph_engine/queries/search.py:resolve_rag()`
- Handler: `knowledge_graph_engine/handlers/rag_handler.py:RAGHandler.rag()`
- Retriever Modes:
  - `vector`: Vector-based retrieval
  - `hybrid`: Combined vector + fulltext

**Response Format**:
```json
{
  "answer": "Generated answer text...",
  "context": [
    {"content": "...", "score": 0.95, "metadata": {...}},
    ...
  ]
}
```

---

## 3. Implementation Phases

### Phase 1: MCP Client Configuration (Week 1)

**Deliverables**:
- ✅ MCP configuration schema for `mcp_kg_engine`
- ✅ Tool definitions in `MCP_CONFIGURATION`
- ✅ Module linking configuration
- ⏳ Connection pooling for GraphQL endpoints
- ⏳ Authentication handling (x-api-key, Part-Id)

**Tasks**:
1. ✅ Define MCP tool schemas for search, rag
2. ✅ Configure `module_links` in `mcp_kg_engine/mcp_kg_engine.py`
3. ⏳ Implement connection pooling in `MCPKGEngine`
4. ⏳ Add authentication middleware support
5. ⏳ Create configuration validation

**Files to Create/Update**:
- `mcp_kg_engine/mcp_kg_engine.py` - MCP configuration
- `mcp_kg_engine/graphql_module.py` - GraphQL module management
- `mcp_kg_engine/config.py` - Configuration validation (new)

---

### Phase 2: GraphQL Schema Alignment (Week 2)

**Deliverables**:
- ⏳ Updated GraphQL types for MCP compatibility
- ⏳ Unified error handling format
- ⏳ Request/response logging
- ⏳ Schema documentation

**Tasks**:
1. ⏳ Review and align `SearchResultType` with MCP output
2. ⏳ Review and align `RAGQueryResultType` with MCP output
3. ⏳ Standardize error response format
4. ⏳ Add request tracking in `models/request.py`
5. ⏳ Update GraphQL schema documentation

**Files to Update**:
- `knowledge_graph_engine/types/search.py` - Result types
- `knowledge_graph_engine/schema.py` - Schema definitions
- `knowledge_graph_engine/handlers/search_handler.py` - Error handling
- `knowledge_graph_engine/handlers/rag_handler.py` - Error handling

---

### Phase 3: Search Integration (Week 3)

**Deliverables**:
- ⏳ MCP search tool fully operational
- ⏳ All 4 search modes working
- ⏳ Pagination support
- ⏳ Filter support
- ⏳ Response formatting

**Tasks**:
1. ⏳ Map MCP search parameters to GraphQL query
2. ⏳ Implement parameter validation
3. ⏳ Support all search modes:
   - `vector`: `SearchHandler._build_retriever()` → VectorRetriever
   - `text2cypher`: `SearchHandler._load_neo4j_schema()` + LLM
   - `vector_cypher`: Vector + custom Cypher
   - `hybrid`: `HybridRetriever`
4. ⏳ Implement result pagination in `_format_results()`
5. ⏳ Add filter support (where applicable)
6. ⏳ Write integration tests

**Testing**:
- Unit tests for parameter mapping
- Integration tests for each search mode
- Performance benchmarks
- Error handling tests

**Files to Update**:
- `mcp_kg_engine/mcp_kg_engine.py` - `search()` method
- `knowledge_graph_engine/queries/search.py` - Query resolvers
- `knowledge_graph_engine/handlers/search_handler.py` - Search logic

---

### Phase 4: RAG Integration (Week 4)

**Deliverables**:
- ⏳ MCP RAG tool fully operational
- ⏳ Custom prompt support
- ⏳ Context retrieval optimization
- ⏳ Answer formatting

**Tasks**:
1. ⏳ Map MCP RAG parameters to GraphQL query
2. ⏳ Implement prompt template handling
3. ⏳ Optimize context retrieval (top_k tuning)
4. ⏳ Implement response formatting
5. ⏳ Add context serialization for JSON output
6. ⏳ Write integration tests

**Testing**:
- Unit tests for RAG parameter mapping
- Integration tests with various prompts
- Context quality validation
- Error scenario testing

**Files to Update**:
- `mcp_kg_engine/mcp_kg_engine.py` - `rag()` method
- `knowledge_graph_engine/queries/search.py` - RAG resolver
- `knowledge_graph_engine/handlers/rag_handler.py` - RAG logic

---

### Phase 5: Authentication & Security (Week 5)

**Deliverables**:
- ⏳ API key authentication
- ⏳ Partition-based authorization
- ⏳ Rate limiting
- ⏳ Request logging

**Tasks**:
1. ⏳ Implement x-api-key validation
2. ⏳ Add Part-Id header handling
3. ⏳ Implement partition-based access control
4. ⏳ Add rate limiting per partition
5. ⏳ Create request audit logging
6. ⏳ Security testing

**Files to Update**:
- `knowledge_graph_engine/handlers/middleware.py` - Auth middleware
- `knowledge_graph_engine/handlers/auth_router.py` - Auth routes
- `knowledge_graph_engine/main.py` - Security configuration

---

### Phase 6: Performance Optimization (Week 6)

**Deliverables**:
- ⏳ Connection pooling
- ⏳ Query caching
- ⏳ Vector index optimization
- ⏳ Load testing results

**Tasks**:
1. ⏳ Implement HTTP connection pooling in `MCPKGEngine`
2. ⏳ Add query result caching
3. ⏳ Optimize Neo4j vector index queries
4. ⏳ Implement request batching where applicable
5. ⏳ Load testing and profiling
6. ⏳ Performance tuning

**Files to Update**:
- `mcp_kg_engine/mcp_kg_engine.py` - Connection management
- `knowledge_graph_engine/handlers/config.py` - Cache configuration
- `knowledge_graph_engine/utils/graph_rag_util.py` - Query optimization

---

### Phase 8: Testing & Documentation (Week 8)

**Deliverables**:
- ⏳ Comprehensive test suite
- ⏳ API documentation
- ⏳ Integration examples
- ⏳ Deployment guide

**Tasks**:
1. ⏳ Unit tests for all MCP tools
2. ⏳ Integration tests (MCP → GraphQL → Neo4j)
3. ⏳ End-to-end tests
4. ⏳ Performance benchmarks
5. ⏳ API documentation (OpenAPI/GraphQL schema)
6. ⏳ Create example client code
7. ⏳ Write deployment guide

**Files to Create**:
- `tests/test_mcp_integration.py` - Integration tests
- `tests/test_mcp_performance.py` - Performance tests
- `docs/API_REFERENCE.md` - API documentation
- `examples/mcp_client_example.py` - Example usage

---

### Phase 9: Deployment (Week 9)

**Deliverables**:
- ⏳ Docker configuration
- ⏳ AWS deployment
- ⏳ Monitoring setup
- ⏳ Production checklist

**Tasks**:
1. ⏳ Create Dockerfile for knowledge_graph_engine
2. ⏳ Create docker-compose.yml for local testing
3. ⏳ Configure AWS Lambda deployment
4. ⏳ Set up CloudWatch monitoring
5. ⏳ Configure health checks
6. ⏳ Production readiness review

**Files to Create**:
- `Dockerfile`
- `docker-compose.yml`
- `.github/workflows/deploy.yml` - CI/CD
- `docs/DEPLOYMENT.md` - Deployment guide

---

## 4. Current Implementation Status

### 4.1 Completed (✅)

1. **MCP Configuration Structure**
   - File: `mcp_kg_engine/mcp_kg_engine.py`
   - MCP tools defined: `search`, `rag`
   - Module links configured
   - Basic tool schemas defined

2. **GraphQL Backend**
   - File: `knowledge_graph_engine/main.py`
   - GraphQL schema operational
   - Search and RAG resolvers implemented
   - Neo4j integration complete

3. **Search Handler**
   - File: `knowledge_graph_engine/handlers/search_handler.py`
   - 4 search modes implemented
   - Pagination support
   - Result formatting

4. **RAG Handler**
   - File: `knowledge_graph_engine/handlers/rag_handler.py`
   - GraphRAG integration
   - Custom prompt support
   - Context serialization

### 4.2 Pending (⏳)

1. **Connection Management**
   - HTTP connection pooling in `MCPKGEngine`
   - Session lifecycle management
   - Retry logic for failed requests

2. **Authentication**
   - x-api-key header propagation
   - Part-Id context passing
   - Token refresh mechanisms

3. **Parameter Mapping**
   - Complete mapping of MCP parameters to GraphQL
   - Validation and sanitization
   - Default value handling

4. **Error Handling**
   - Unified error format between MCP and GraphQL
   - Proper error propagation
   - Retry strategies

5. **Testing**
   - MCP client integration tests
   - End-to-end tests
   - Performance benchmarks

---

## 5. API Reference

### 5.1 MCP Tools

#### Tool: `search`

```python
# MCP Client Usage
from mcp import ClientSession

async with ClientSession(server_streams) as session:
    result = await session.call_tool("search", {
        "query_text": "Find products related to machine learning",
        "data_type": "product",
        "similarity_search": True,
        "page": 1,
        "limit": 10
    })
```

**GraphQL Equivalent**:
```graphql
query Search($queryText: String!, $searchMode: String, $page: Int, $limit: Int) {
  search(queryText: $queryText, searchMode: $searchMode, page: $page, limit: $limit) {
    results
    total
    page
    limit
  }
}
```

#### Tool: `rag`

```python
# MCP Client Usage
result = await session.call_tool("rag", {
    "query_text": "What are the key features of our AI platform?",
    "prompt": "You are a helpful assistant answering questions about our products."
})
```

**GraphQL Equivalent**:
```graphql
query RAG($queryText: String!, $prompt: String) {
  rag(queryText: $queryText, prompt: $prompt) {
    answer
    context {
      content
      score
      metadata
    }
  }
}
```

---

## 6. Configuration

### 6.1 MCP Configuration

```python
# mcp_kg_engine/mcp_kg_engine.py
MCP_CONFIGURATION = {
    "tools": [
        {
            "name": "search",
            "description": "Search the knowledge graph...",
            "inputSchema": {...},
        },
        {
            "name": "rag",
            "description": "Perform RAG query...",
            "inputSchema": {...},
        },
    ],
    "graphql_modules": {
        "ai_kg_engine": {
            "endpoint": "https://api.example.com/{endpoint_id}/graphql",
            "x_api_key": "<api_key>",
        },
    },
}
```

### 6.2 Environment Variables

```bash
# Required
export ENDPOINT_ID="your-endpoint-id"
export PART_ID="your-part-id"
export X_API_KEY="your-api-key"

# Neo4j
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="password"
export NEO4J_DATABASE="neo4j"

# LLM
export OPENAI_API_KEY="sk-..."
export LLM_NAME="gpt-4o"

# Embeddings
export EMBEDDING_MODEL="text-embedding-3-small"
```

---

## 7. Testing Strategy

### 7.1 Test Categories

1. **Unit Tests**: Parameter validation, mapping functions
2. **Integration Tests**: MCP → GraphQL → Neo4j
3. **End-to-End Tests**: Full workflow testing
4. **Performance Tests**: Query latency, throughput

### 7.2 Test Commands

```bash
# Run all tests
pytest tests/ -v

# MCP integration tests
pytest tests/test_mcp_integration.py -v

# Performance tests
pytest tests/test_mcp_performance.py -v --benchmark

# Search tests
pytest tests/test_search.py -v -k "search"

# RAG tests
pytest tests/test_search_rag.py -v
```

### 7.3 Test Fixtures

```python
# conftest.py
@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    return MCPKGEngine(
        logger=logging.getLogger("test"),
        endpoint="http://localhost:8000/graphql",
        x_api_key="test-key",
    )

```

---

## 8. Performance Considerations

### 8.1 Current Metrics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Vector Search | ~50-100ms | Depends on top_k |
| Hybrid Search | ~100-200ms | Vector + fulltext |
| Text2Cypher | ~500-1000ms | LLM generation time |
| RAG Query | ~1-3s | Search + LLM generation |

### 8.2 Optimization Strategies

1. **Connection Pooling**: Reuse HTTP connections
2. **Query Caching**: Cache frequent searches
3. **Batch Processing**: Batch MCP tool requests where applicable
4. **Async Operations**: Async GraphQL queries
5. **Index Tuning**: Optimize Neo4j indexes

---

## 9. Troubleshooting

### 9.1 Common Issues

1. **Connection Timeout**
   - Check Neo4j URI
   - Verify network connectivity
   - Increase timeout in Config

2. **Authentication Error**
   - Verify x-api-key
   - Check Part-Id header
   - Validate endpoint_id/part_id

3. **Search Returns Empty**
   - Check partition_key exists
   - Verify vector index exists
   - Review query_text relevance

4. **RAG Poor Quality**
   - Tune top_k parameter
   - Review prompt template
   - Check context relevance

### 9.2 Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Add verbose output
result = await session.call_tool("search", {
    "query_text": "test",
    "debug": True
})
```

---

## 10. Next Steps

### Immediate Actions (This Week)

1. ⏳ Review current implementation gaps
2. ⏳ Set up local development environment
3. ⏳ Run existing tests
4. ⏳ Document configuration requirements

### Short Term (Next 4 Weeks)

1. ⏳ Complete Phase 1: MCP Client Configuration
2. ⏳ Complete Phase 2: GraphQL Schema Alignment
3. ⏳ Complete Phase 3: Search Integration
4. ⏳ Complete Phase 4: RAG Integration

### Medium Term (Weeks 5-8)

1. ⏳ Complete Phase 5: Extract Integration
2. ⏳ Complete Phase 6: Authentication & Security
3. ⏳ Complete Phase 7: Performance Optimization
4. ⏳ Complete Phase 8: Testing & Documentation

### Long Term (Week 9+)

1. ⏳ Complete Phase 9: Deployment
2. ⏳ Production deployment
3. ⏳ Monitoring and maintenance
4. ⏳ Feature enhancements

---

## 11. Resources

### Code Repositories

- `mcp_kg_engine`: MCP client implementation
- `knowledge_graph_engine`: GraphQL backend and Neo4j integration

### Documentation

- [Neo4j GraphRAG Python](https://neo4j.com/docs/graphrag-python/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Neo4j Vector Search](https://neo4j.com/docs/cypher-manual/current/indexes/vector/)

### Key Files

- `mcp_kg_engine/mcp_kg_engine.py` - MCP client main class
- `knowledge_graph_engine/main.py` - GraphQL engine entry point
- `knowledge_graph_engine/handlers/search_handler.py` - Search implementation
- `knowledge_graph_engine/handlers/rag_handler.py` - RAG implementation
- `knowledge_graph_engine/handlers/extractor.py` - Extract implementation

---

## 12. Contact & Support

For questions or issues:
- Review this development plan
- Check existing test files for examples
- Refer to AGENTS.md for coding guidelines
- Consult the knowledge_graph_engine README

---

**Document Version**: 1.0
**Last Updated**: 2026-03-31
**Status**: Draft - Pending Review
