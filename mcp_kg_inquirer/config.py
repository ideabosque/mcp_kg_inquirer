"""
Configuration management for MCP KG Inquirer.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration settings for MCPKGInquirer client.
    
    Attributes:
        endpoint_id: The endpoint identifier for the Knowledge Graph Engine.
        part_id: The partition identifier for tenant isolation.
        api_key: API key for authentication (optional if bearer_token provided).
        bearer_token: Bearer token for OAuth/JWT authentication (optional).
        base_url: Base URL for the API (default: from environment or localhost).
        timeout: Request timeout in seconds (default: 30).
        max_retries: Maximum number of retry attempts (default: 3).
        retry_delay: Delay between retries in seconds (default: 1.0).
    """
    
    endpoint_id: str
    part_id: str
    api_key: Optional[str] = None
    bearer_token: Optional[str] = None
    base_url: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    
    def __post_init__(self):
        """Validate and set defaults after initialization."""
        if not self.endpoint_id:
            raise ValueError("endpoint_id is required")
        if not self.part_id:
            raise ValueError("part_id is required")
        
        # At least one authentication method is required
        if not self.api_key and not self.bearer_token:
            raise ValueError("Either api_key or bearer_token is required")
        
        # Set base_url from environment if not provided
        if self.base_url is None:
            self.base_url = os.environ.get(
                "KGE_BASE_URL",
                "http://localhost:8000"
            )
    
    @property
    def graphql_endpoint(self) -> str:
        """Get the GraphQL endpoint URL."""
        return f"{self.base_url}/{self.endpoint_id}/knowledge_graph_graphql"
    
    @property
    def partition_key(self) -> str:
        """Get the partition key for tenant isolation."""
        return f"{self.endpoint_id}#{self.part_id}"
    
    @property
    def headers(self) -> dict:
        """Get the HTTP headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "Part-Id": self.part_id,
        }
        
        # Add authentication header
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.api_key:
            headers["x-api-key"] = self.api_key
        
        return headers
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create a Config instance from environment variables.
        
        Environment variables:
            KGE_ENDPOINT_ID: The endpoint identifier (required)
            KGE_PART_ID: The partition identifier (required)
            KGE_API_KEY: The API key (required if no bearer token)
            KGE_BEARER_TOKEN: Bearer token for OAuth/JWT auth (optional, preferred)
            KGE_BASE_URL: The base URL (optional)
            KGE_TIMEOUT: Request timeout in seconds (optional)
            KGE_MAX_RETRIES: Maximum retries (optional)
            KGE_RETRY_DELAY: Retry delay in seconds (optional)
        Returns:
            Config instance with values from environment
        
        Raises:
            ValueError: If required environment variables are missing
        """
        endpoint_id = os.environ.get("KGE_ENDPOINT_ID")
        part_id = os.environ.get("KGE_PART_ID")
        api_key = os.environ.get("KGE_API_KEY") or None
        bearer_token = os.environ.get("KGE_BEARER_TOKEN") or None
        
        if not endpoint_id:
            raise ValueError("KGE_ENDPOINT_ID environment variable is required")
        if not part_id:
            raise ValueError("KGE_PART_ID environment variable is required")
        
        # At least one auth method is required
        if not api_key and not bearer_token:
            raise ValueError(
                "Either KGE_API_KEY or KGE_BEARER_TOKEN environment variable is required"
            )
        
        return cls(
            endpoint_id=endpoint_id,
            part_id=part_id,
            api_key=api_key,
            bearer_token=bearer_token,
            base_url=os.environ.get("KGE_BASE_URL"),
            timeout=float(os.environ.get("KGE_TIMEOUT", "30.0")),
            max_retries=int(os.environ.get("KGE_MAX_RETRIES", "3")),
            retry_delay=float(os.environ.get("KGE_RETRY_DELAY", "1.0")),
        )
