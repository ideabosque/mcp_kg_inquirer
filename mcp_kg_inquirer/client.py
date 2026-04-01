"""MCP KG Inquirer client for Knowledge Graph Engine integration."""

import asyncio
import json
import logging
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from mcp_kg_inquirer.config import Config
from mcp_kg_inquirer.exceptions import (
    ConnectionError,
    MCPKGInquirerError,
    RateLimitError,
    TimeoutError,
)
from mcp_kg_inquirer.graphql_module import GraphQLModule
from mcp_kg_inquirer.rag import (
    RAGResponse,
    build_rag_request,
    get_prompt_for_use_case,
    parse_rag_response,
)
from mcp_kg_inquirer.search import (
    SearchResponse,
    build_search_request,
    parse_search_response,
)

MCP_CONFIGURATION = {
    "tools": [
        {
            "name": "search",
            "description": "Searches for information in the knowledge graph. Accepts a query text and optional filters to search across various data types. Returns relevant search results with pagination.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "Search query text",
                    },
                    "data_type": {
                        "type": "string",
                        "description": "Type of data to search",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Additional filters for the search",
                    },
                    "similarity_search": {
                        "type": "boolean",
                        "description": "Enable similarity search",
                    },
                    "relevance_search": {
                        "type": "boolean",
                        "description": "Enable relevance search",
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results per page",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Additional prompt for search context",
                    },
                    "search_mode": {
                        "type": "string",
                        "description": "Explicit search mode override",
                    },
                },
                "required": ["query_text"],
            },
            "annotations": None,
        },
        {
            "name": "rag",
            "description": "Performs Retrieval-Augmented Generation (RAG) to answer questions based on the knowledge graph. Accepts a query text and optional prompt to generate contextually relevant answers using information retrieved from the knowledge graph.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "Query text for RAG",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Additional prompt for RAG context",
                    },
                    "use_case": {
                        "type": "string",
                        "description": "Predefined prompt use case",
                    },
                },
                "required": ["query_text"],
            },
            "annotations": None,
        },
    ],
    "resources": [],
    "prompts": [],
    "module_links": [
        {
            "type": "tool",
            "name": "search",
            "module_name": "mcp_kg_inquirer",
            "class_name": "MCPKGInquirer",
            "function_name": "search",
            "return_type": "text",
        },
        {
            "type": "tool",
            "name": "rag",
            "module_name": "mcp_kg_inquirer",
            "class_name": "MCPKGInquirer",
            "function_name": "rag",
            "return_type": "text",
        },
    ],
    "modules": [
        {
            "package_name": "mcp_kg_inquirer",
            "module_name": "mcp_kg_inquirer",
            "class_name": "MCPKGInquirer",
            "setting": {
                "keyword": "knowledge_graph",
                "graphql_modules": {
                    "ai_kg_engine": {
                        "class_name": "Query",
                        "endpoint": "https://api.example.com/{endpoint_id}/graphql",
                        "x_api_key": "<api_key>",
                    },
                },
            },
        }
    ],
}


class CircuitBreaker:
    """Circuit breaker pattern for resilience."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def is_open(self) -> bool:
        if self.state == "open":
            if self.last_failure_time is not None:
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = "half-open"
                    return False
            return True
        return False

    def reset(self) -> None:
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"

    def get_state(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self.last_failure_time,
        }

    def is_closed(self) -> bool:
        return self.state == "closed"

    def is_half_open(self) -> bool:
        return self.state == "half-open"


class MCPKGInquirer:
    """MCP client for Knowledge Graph Engine integration."""
    
    def __init__(
        self,
        logger: logging.Logger,
        **setting: Dict[str, Any],
    ):
        """Initialize the MCP KG Inquirer client."""
        self.logger = logger
        self.setting = setting
        self._endpoint_id = None
        self._part_id = None
        self._graphql_modules = {}

        self._endpoint_id = setting.get("endpoint_id")
        self._part_id = setting.get("part_id")

        self.config = Config(
            endpoint_id=self._endpoint_id,
            part_id=self._part_id,
            api_key=setting.get("api_key"),
            bearer_token=setting.get("bearer_token"),
            base_url=setting.get("base_url"),
            timeout=setting.get("timeout", 30.0),
            max_retries=setting.get("max_retries", 3),
            retry_delay=setting.get("retry_delay", 1.0),
        )
        
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=setting.get("circuit_breaker_threshold", 5),
            recovery_timeout=setting.get("circuit_breaker_timeout", 60.0),
        )

    @property
    def endpoint_id(self) -> str | None:
        return self._endpoint_id

    @endpoint_id.setter
    def endpoint_id(self, value: str):
        self._endpoint_id = value

    @property
    def part_id(self) -> str | None:
        return self._part_id

    @part_id.setter
    def part_id(self, value: str):
        self._part_id = value

    def get_graphql_module(self, module_name: str) -> GraphQLModule | None:
        """Get a GraphQL module by name."""
        if not self._graphql_modules.get(module_name):
            self._graphql_modules[module_name] = GraphQLModule(
                endpoint_id=self.endpoint_id,
                module_name=module_name,
                class_name=self.setting.get("graphql_modules", {})
                .get(module_name, {})
                .get("class_name"),
                endpoint=self.setting.get("graphql_modules", {})
                .get(module_name, {})
                .get("endpoint"),
                x_api_key=self.setting.get("graphql_modules", {})
                .get(module_name, {})
                .get("x_api_key"),
            )

        return self._graphql_modules.get(module_name)
    
    @classmethod
    def from_env(cls, logger: logging.Logger) -> "MCPKGInquirer":
        """Create a client from environment variables."""
        config = Config.from_env()
        return cls(
            logger,
            endpoint_id=config.endpoint_id,
            part_id=config.part_id,
            api_key=config.api_key,
            bearer_token=config.bearer_token,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
        )

    def _post_graphql_sync(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = urllib.request.Request(
            self.config.graphql_endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=self.config.headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                status_code = getattr(response, "status", response.getcode())
                body = response.read().decode("utf-8")
                data = json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            details = {"status": exc.code, "url": self.config.graphql_endpoint}
            if exc.code == 401:
                raise ConnectionError("Authentication failed", details)
            if exc.code == 429:
                raise RateLimitError("Rate limit exceeded", details)
            if exc.code >= 500:
                raise ConnectionError("Server error", details)
            raise ConnectionError(f"Request failed with status {exc.code}", details)
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, (socket.timeout, TimeoutError)):
                raise TimeoutError(
                    f"Request timed out after {self.config.timeout} seconds",
                    {"endpoint": self.config.graphql_endpoint},
                )
            raise ConnectionError(
                f"Connection failed: {reason}",
                {"endpoint": self.config.graphql_endpoint, "error": str(reason)},
            )
        except socket.timeout:
            raise TimeoutError(
                f"Request timed out after {self.config.timeout} seconds",
                {"endpoint": self.config.graphql_endpoint},
            )

        if status_code == 200:
            return data
        if status_code == 401:
            raise ConnectionError(
                "Authentication failed",
                {"status": status_code, "url": self.config.graphql_endpoint},
            )
        if status_code == 429:
            raise RateLimitError(
                "Rate limit exceeded",
                {"status": status_code, "url": self.config.graphql_endpoint},
            )
        if status_code >= 500:
            raise ConnectionError(
                "Server error",
                {"status": status_code, "url": self.config.graphql_endpoint},
            )
        raise ConnectionError(
            f"Request failed with status {status_code}",
            {"status": status_code, "url": self.config.graphql_endpoint},
        )

    async def _post_graphql(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await asyncio.to_thread(self._post_graphql_sync, payload)
    
    async def _execute_graphql(
        self,
        query: str,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a GraphQL query.
        
        Args:
            query: The GraphQL query string.
            variables: The query variables.
        
        Returns:
            The response data.
        
        Raises:
            ConnectionError: If connection fails.
            AuthenticationError: If authentication fails.
            MCPKGInquirerError: For other errors.
        """
        # Check circuit breaker
        if self.circuit_breaker.is_open():
            raise ConnectionError(
                "Circuit breaker is open - too many recent failures",
                {"state": self.circuit_breaker.state}
            )
        
        payload = {
            "query": query,
            "variables": variables,
        }
        
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries):
            try:
                response = await self._post_graphql(payload)
                self.circuit_breaker.record_success()
                return response
            except (ConnectionError, TimeoutError, RateLimitError) as exc:
                self.circuit_breaker.record_failure()
                last_error = exc
                if attempt == self.config.max_retries - 1:
                    raise
                await asyncio.sleep(self.config.retry_delay)
            except Exception as exc:
                self.circuit_breaker.record_failure()
                raise MCPKGInquirerError(
                    f"Unexpected error: {str(exc)}",
                    {"error": str(exc)},
                ) from exc

        if last_error is not None:
            raise last_error
        raise MCPKGInquirerError("Unexpected error", {"error": "Unknown request failure"})
    
    async def search(
        self,
        query_text: str,
        data_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        similarity_search: bool = False,
        relevance_search: bool = False,
        page: int = 1,
        limit: int = 10,
        prompt: Optional[str] = None,
        search_mode: Optional[str] = None,
    ) -> SearchResponse:
        """Search the knowledge graph.
        
        Args:
            query_text: The search query text.
            data_type: Optional data type filter.
            filters: Optional filters to apply.
            similarity_search: Whether to use similarity search (vector mode).
            relevance_search: Whether to use relevance search (hybrid mode).
            page: Page number for pagination.
            limit: Number of results per page.
            prompt: Optional custom prompt for text2cypher mode.
            search_mode: Explicit search mode (overrides flags).
        
        Returns:
            A SearchResponse with results.
        
        Raises:
            ValidationError: If parameters are invalid.
            SearchError: If the search fails.
            ConnectionError: If connection fails.
        """
        request = build_search_request(
            query_text=query_text,
            data_type=data_type,
            filters=filters,
            similarity_search=similarity_search,
            relevance_search=relevance_search,
            page=page,
            limit=limit,
            prompt=prompt,
            search_mode=search_mode,
        )
        
        response = await self._execute_graphql(
            query=request["query"],
            variables=request["variables"],
        )
        
        return parse_search_response(response)
    
    async def search_vector(
        self,
        query_text: str,
        data_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        limit: int = 10,
    ) -> SearchResponse:
        """Search using vector similarity.
        
        Args:
            query_text: The search query text.
            data_type: Optional data type filter.
            filters: Optional filters to apply.
            page: Page number for pagination.
            limit: Number of results per page.
        
        Returns:
            A SearchResponse with results.
        """
        return await self.search(
            query_text=query_text,
            data_type=data_type,
            filters=filters,
            similarity_search=True,
            page=page,
            limit=limit,
        )
    
    async def search_hybrid(
        self,
        query_text: str,
        data_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        limit: int = 10,
    ) -> SearchResponse:
        """Search using hybrid (vector + fulltext) approach.
        
        Args:
            query_text: The search query text.
            data_type: Optional data type filter.
            filters: Optional filters to apply.
            page: Page number for pagination.
            limit: Number of results per page.
        
        Returns:
            A SearchResponse with results.
        """
        return await self.search(
            query_text=query_text,
            data_type=data_type,
            filters=filters,
            relevance_search=True,
            page=page,
            limit=limit,
        )
    
    async def rag(
        self,
        query_text: str,
        prompt: Optional[str] = None,
        use_case: Optional[str] = None,
    ) -> RAGResponse:
        """Perform a RAG query.
        
        Args:
            query_text: The question to answer.
            prompt: Optional custom system prompt.
            use_case: Use case for default prompt (default, summary, explanation).
        
        Returns:
            A RAGResponse with answer and context.
        
        Raises:
            ValidationError: If parameters are invalid.
            RAGError: If the RAG query fails.
            ConnectionError: If connection fails.
        """
        # Use default prompt if use_case is specified and no custom prompt
        if prompt is None and use_case:
            prompt = get_prompt_for_use_case(use_case)
        
        request = build_rag_request(
            query_text=query_text,
            prompt=prompt,
        )
        
        response = await self._execute_graphql(
            query=request["query"],
            variables=request["variables"],
        )
        
        return parse_rag_response(response)
    
    async def rag_with_context(
        self,
        query_text: str,
        prompt: Optional[str] = None,
        top_k: int = 5,
    ) -> RAGResponse:
        """Perform a RAG query with explicit context retrieval.
        
        This method is an alias for rag() but makes the top_k parameter
        explicit for when you want to control context retrieval size.
        
        Args:
            query_text: The question to answer.
            prompt: Optional custom system prompt.
            top_k: Number of context documents to retrieve.
        
        Returns:
            A RAGResponse with answer and context.
        """
        return await self.rag(
            query_text=query_text,
            prompt=prompt,
        )
    
    async def batch_search(
        self,
        queries: List[str],
        data_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        similarity_search: bool = False,
        relevance_search: bool = False,
        page: int = 1,
        limit: int = 10,
    ) -> List[SearchResponse]:
        """Execute multiple search queries in parallel.
        
        Args:
            queries: List of search query texts.
            data_type: Optional data type filter.
            filters: Optional filters to apply.
            similarity_search: Whether to use similarity search.
            relevance_search: Whether to use relevance search.
            page: Page number for pagination.
            limit: Number of results per page.
        
        Returns:
            List of SearchResponse objects, one for each query.
        """
        import asyncio
        
        tasks = [
            self.search(
                query_text=query,
                data_type=data_type,
                filters=filters,
                similarity_search=similarity_search,
                relevance_search=relevance_search,
                page=page,
                limit=limit,
            )
            for query in queries
        ]
        
        return await asyncio.gather(*tasks)
    
    async def batch_rag(
        self,
        queries: List[str],
        prompt: Optional[str] = None,
        use_case: Optional[str] = None,
    ) -> List[RAGResponse]:
        """Execute multiple RAG queries in parallel.
        
        Args:
            queries: List of questions to answer.
            prompt: Optional custom system prompt.
            use_case: Use case for default prompt.
        
        Returns:
            List of RAGResponse objects, one for each query.
        """
        import asyncio
        
        tasks = [
            self.rag(query_text=query, prompt=prompt, use_case=use_case)
            for query in queries
        ]
        
        return await asyncio.gather(*tasks)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the connection.
        
        Returns:
            Dictionary with health status information.
        
        Raises:
            ConnectionError: If health check fails.
        """
        try:
            # Simple query to check connectivity
            response = await self._execute_graphql(
                query="{ __typename }",
                variables={},
            )
            if response.get("errors"):
                raise MCPKGInquirerError(
                    "Health check returned GraphQL errors",
                    {"errors": response["errors"]},
                )
            return {
                "healthy": True,
                "endpoint": self.config.graphql_endpoint,
                "partition_key": self.config.partition_key,
                "circuit_breaker": self.circuit_breaker.get_state(),
            }
        except Exception as e:
            return {
                "healthy": False,
                "endpoint": self.config.graphql_endpoint,
                "partition_key": self.config.partition_key,
                "error": str(e),
                "circuit_breaker": self.circuit_breaker.get_state(),
            }
    
    async def close(self) -> None:
        """Close the client."""
        self.logger.info("MCPKGInquirer client closed")
    
    async def __aenter__(self) -> "MCPKGInquirer":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
