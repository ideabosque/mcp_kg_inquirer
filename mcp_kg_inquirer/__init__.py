"""MCP KG Inquirer package."""

from mcp_kg_inquirer.client import MCP_CONFIGURATION, CircuitBreaker, MCPKGInquirer
from mcp_kg_inquirer.config import Config
from mcp_kg_inquirer.exceptions import (
    AuthenticationError,
    ConnectionError,
    MCPKGInquirerError,
    RAGError,
    RateLimitError,
    SearchError,
    TimeoutError,
    ValidationError,
)
from mcp_kg_inquirer.graphql_module import GraphQLModule
from mcp_kg_inquirer.rag import (
    DEFAULT_PROMPT,
    EXPLANATION_PROMPT,
    SUMMARY_PROMPT,
    RAGContext,
    RAGRequest,
    RAGResponse,
)
from mcp_kg_inquirer.search import (
    SearchMode,
    SearchRequest,
    SearchResponse,
    SearchResult,
)

__version__ = "0.1.0"
__author__ = "SilvaEngine Team"

__all__ = [
    # Client
    "MCPKGInquirer",
    "MCP_CONFIGURATION",
    "Config",
    "CircuitBreaker",
    "GraphQLModule",
    # Exceptions
    "MCPKGInquirerError",
    "ConnectionError",
    "AuthenticationError",
    "SearchError",
    "RAGError",
    "ValidationError",
    "TimeoutError",
    "RateLimitError",
    # Search
    "SearchMode",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    # RAG
    "RAGRequest",
    "RAGResponse",
    "RAGContext",
    "DEFAULT_PROMPT",
    "SUMMARY_PROMPT",
    "EXPLANATION_PROMPT",
]
