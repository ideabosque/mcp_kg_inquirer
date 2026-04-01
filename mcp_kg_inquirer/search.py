"""
Search implementation for MCP KG Inquirer.

Supports 4 search modes:
- vector: Semantic similarity search using embeddings
- text2cypher: LLM-generated Cypher queries
- vector_cypher: Vector search with custom Cypher traversal
- hybrid: Combined vector and fulltext search
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from mcp_kg_inquirer.exceptions import SearchError, ValidationError


class SearchMode(str, Enum):
    """Search mode enumeration."""

    VECTOR = "vector"
    TEXT2CYPHER = "text2cypher"
    VECTOR_CYPHER = "vector_cypher"
    HYBRID = "hybrid"


@dataclass
class SearchRequest:
    """Search request parameters.

    Attributes:
        query_text: The search query text.
        data_type: Optional data type filter.
        filters: Optional filters to apply.
        similarity_search: Whether to use similarity search (vector mode).
        relevance_search: Whether to use relevance search (hybrid mode).
        page: Page number for pagination (default: 1).
        limit: Number of results per page (default: 10).
        prompt: Optional custom prompt for text2cypher mode.
    """

    query_text: str
    data_type: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    similarity_search: bool = False
    relevance_search: bool = False
    page: int = 1
    limit: int = 10
    prompt: Optional[str] = None

    def __post_init__(self):
        """Validate request parameters."""
        if not self.query_text or not self.query_text.strip():
            raise ValidationError("query_text is required and cannot be empty")

        if self.page < 1:
            raise ValidationError("page must be >= 1")

        if self.limit < 1 or self.limit > 100:
            raise ValidationError("limit must be between 1 and 100")

    def to_graphql_variables(self) -> Dict[str, Any]:
        """Convert request to GraphQL variables.

        Returns:
            Dictionary of GraphQL variables.
        """
        variables = {
            "queryText": self.query_text,
        }

        # Determine search mode from flags
        if self.similarity_search and not self.relevance_search:
            variables["searchMode"] = SearchMode.VECTOR.value
        elif self.relevance_search and not self.similarity_search:
            variables["searchMode"] = SearchMode.HYBRID.value
        elif self.similarity_search and self.relevance_search:
            # If both are set, prefer hybrid
            variables["searchMode"] = SearchMode.HYBRID.value

        if self.data_type:
            variables["dataType"] = self.data_type

        if self.filters:
            variables["filters"] = self.filters

        variables["page"] = self.page
        variables["limit"] = self.limit

        if self.prompt:
            variables["prompt"] = self.prompt

        return variables


@dataclass
class SearchResult:
    """Search result item.

    Attributes:
        content: The content of the result.
        score: The relevance score.
        metadata: Additional metadata.
        node_id: The node ID in the graph.
        labels: Node labels.
    """

    content: str
    score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    node_id: Optional[str] = None
    labels: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResult":
        """Create a SearchResult from a dictionary.

        Args:
            data: The result dictionary.

        Returns:
            A SearchResult instance.
        """
        return cls(
            content=data.get("content", ""),
            score=data.get("score", 0.0),
            metadata=data.get("metadata"),
            node_id=data.get("node_id") or data.get("nodeId"),
            labels=data.get("labels"),
        )


@dataclass
class SearchResponse:
    """Search response.

    Attributes:
        results: List of search results.
        total: Total number of results.
        page: Current page number.
        limit: Results per page.
    """

    results: List[SearchResult] = field(default_factory=list)
    total: int = 0
    page: int = 1
    limit: int = 10

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResponse":
        """Create a SearchResponse from a dictionary.

        Args:
            data: The response dictionary.

        Returns:
            A SearchResponse instance.
        """
        results_data = data.get("results", [])
        results = [SearchResult.from_dict(r) for r in results_data]

        return cls(
            results=results,
            total=data.get("total", len(results)),
            page=data.get("page", 1),
            limit=data.get("limit", 10),
        )


# GraphQL query for search
SEARCH_QUERY = """
query Search($queryText: String!, $searchMode: String, $indexName: String, $retrievalQuery: String, $topK: Int, $page: Int, $limit: Int) {
  search(queryText: $queryText, searchMode: $searchMode, indexName: $indexName, retrievalQuery: $retrievalQuery, topK: $topK, page: $page, limit: $limit) {
    results
    total
    page
    limit
  }
}
"""


def build_search_request(
    query_text: str,
    data_type: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    similarity_search: bool = False,
    relevance_search: bool = False,
    page: int = 1,
    limit: int = 10,
    prompt: Optional[str] = None,
    search_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a GraphQL search request.

    Args:
        query_text: The search query text.
        data_type: Optional data type filter.
        filters: Optional filters to apply.
        similarity_search: Whether to use similarity search.
        relevance_search: Whether to use relevance search.
        page: Page number for pagination.
        limit: Number of results per page.
        prompt: Optional custom prompt.
        search_mode: Explicit search mode (overrides flags).

    Returns:
        Dictionary with query and variables for GraphQL request.

    Raises:
        ValidationError: If parameters are invalid.
    """
    request = SearchRequest(
        query_text=query_text,
        data_type=data_type,
        filters=filters,
        similarity_search=similarity_search,
        relevance_search=relevance_search,
        page=page,
        limit=limit,
        prompt=prompt,
    )

    variables = request.to_graphql_variables()

    # Override with explicit search mode if provided
    if search_mode:
        variables["searchMode"] = search_mode

    return {
        "query": SEARCH_QUERY,
        "variables": variables,
    }


def parse_search_response(response: Dict[str, Any]) -> SearchResponse:
    """Parse a GraphQL search response.

    Args:
        response: The raw GraphQL response.

    Returns:
        A SearchResponse instance.

    Raises:
        SearchError: If the response indicates an error.
    """
    if "errors" in response:
        errors = response.get("errors", [])
        error_msg = errors[0].get("message", "Unknown error") if errors else "Unknown error"
        raise SearchError(f"GraphQL error: {error_msg}", {"errors": errors})

    data = response.get("data", {})
    search_data = data.get("search", {})

    return SearchResponse.from_dict(search_data)
