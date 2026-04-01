"""
Custom exceptions for MCP KG Inquirer.
"""

from typing import Any, Optional


class MCPKGInquirerError(Exception):
    """Base exception for MCP KG Inquirer errors."""

    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class ConnectionError(MCPKGInquirerError):
    """Raised when connection to the Knowledge Graph Engine fails."""

    def __init__(self, message: str = "Failed to connect to Knowledge Graph Engine", details: Optional[Any] = None):
        super().__init__(message, details)


class AuthenticationError(MCPKGInquirerError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", details: Optional[Any] = None):
        super().__init__(message, details)


class SearchError(MCPKGInquirerError):
    """Raised when a search operation fails."""

    def __init__(self, message: str = "Search operation failed", details: Optional[Any] = None):
        super().__init__(message, details)


class RAGError(MCPKGInquirerError):
    """Raised when a RAG operation fails."""

    def __init__(self, message: str = "RAG operation failed", details: Optional[Any] = None):
        super().__init__(message, details)


class ValidationError(MCPKGInquirerError):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation failed", details: Optional[Any] = None):
        super().__init__(message, details)


class TimeoutError(MCPKGInquirerError):
    """Raised when a request times out."""

    def __init__(self, message: str = "Request timed out", details: Optional[Any] = None):
        super().__init__(message, details)


class RateLimitError(MCPKGInquirerError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Any] = None):
        super().__init__(message, details)