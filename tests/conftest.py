"""Test configuration and fixtures for MCP KG Inquirer."""

import asyncio
import logging
from pathlib import Path

import pytest
from dotenv import load_dotenv

from mcp_kg_inquirer.client import MCPKGInquirer
from mcp_kg_inquirer.config import Config

# Load environment variables from .env file if it exists
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
elif (Path(__file__).parent.parent / ".env").exists():
    load_dotenv(Path(__file__).parent.parent / ".env")


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def config():
    """Create a test configuration with API key."""
    return Config(
        endpoint_id="test-endpoint",
        part_id="test-partition",
        api_key="test-api-key",
        base_url="http://localhost:8000",
        timeout=30.0,
        max_retries=3,
        retry_delay=1.0,
    )


@pytest.fixture
def config_bearer():
    """Create a test configuration with bearer token."""
    return Config(
        endpoint_id="test-endpoint",
        part_id="test-partition",
        bearer_token="test-jwt-token",
        base_url="http://localhost:8000",
        timeout=30.0,
        max_retries=3,
        retry_delay=1.0,
    )


@pytest.fixture
def client(config):
    """Create a test client with API key authentication."""
    return MCPKGInquirer(
        logging.getLogger("tests.client"),
        endpoint_id=config.endpoint_id,
        part_id=config.part_id,
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=config.timeout,
        max_retries=config.max_retries,
        retry_delay=config.retry_delay,
    )


@pytest.fixture
def client_bearer(config_bearer):
    """Create a test client with bearer token authentication."""
    return MCPKGInquirer(
        logging.getLogger("tests.client_bearer"),
        endpoint_id=config_bearer.endpoint_id,
        part_id=config_bearer.part_id,
        bearer_token=config_bearer.bearer_token,
        base_url=config_bearer.base_url,
        timeout=config_bearer.timeout,
        max_retries=config_bearer.max_retries,
        retry_delay=config_bearer.retry_delay,
    )


@pytest.fixture
def sample_search_response():
    """Create a sample search response."""
    return {
        "data": {
            "search": {
                "results": [
                    {
                        "content": "Machine learning is a subset of AI...",
                        "score": 0.95,
                        "metadata": {"source": "wiki", "page": 1},
                        "nodeId": "node-001",
                        "labels": ["Concept"],
                    },
                    {
                        "content": "Deep learning uses neural networks...",
                        "score": 0.88,
                        "metadata": {"source": "wiki", "page": 2},
                        "nodeId": "node-002",
                        "labels": ["Concept"],
                    },
                ],
                "total": 2,
                "page": 1,
                "limit": 10,
            }
        }
    }


@pytest.fixture
def sample_rag_response():
    """Create a sample RAG response."""
    return {
        "data": {
            "rag": {
                "answer": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
                "context": [
                    {
                        "content": "Machine learning is a subset of AI...",
                        "score": 0.95,
                        "metadata": {"source": "wiki"},
                    },
                    {
                        "content": "Deep learning uses neural networks...",
                        "score": 0.88,
                        "metadata": {"source": "wiki"},
                    },
                ],
                "model": "gpt-4o",
                "latencyMs": 1500.0,
            }
        }
    }


@pytest.fixture
def sample_error_response():
    """Create a sample error response."""
    return {
        "errors": [
            {
                "message": "Authentication failed",
                "extensions": {"code": "UNAUTHENTICATED"},
            }
        ]
    }


@pytest.fixture
def sample_empty_search_response():
    """Create a sample empty search response."""
    return {
        "data": {
            "search": {
                "results": [],
                "total": 0,
                "page": 1,
                "limit": 10,
            }
        }
    }


@pytest.fixture
def sample_health_response():
    """Create a sample health check response."""
    return {
        "data": {
            "__typename": "Query"
        }
    }


@pytest.fixture
def config_from_env():
    """Create a configuration from environment variables.
    
    This fixture is used for integration tests that need to connect
    to a real Knowledge Graph Engine instance.
    
    Set environment variables in tests/.env or:
        KGE_ENDPOINT_ID=test-endpoint
        KGE_PART_ID=test-partition
        KGE_API_KEY=your-api-key
        KGE_BASE_URL=http://localhost:8000
    """
    try:
        return Config.from_env()
    except ValueError as e:
        pytest.skip(f"Environment configuration not available: {e}")


@pytest.fixture
def client_from_env(config_from_env):
    """Create a client from environment configuration.
    
    This fixture is used for integration tests that need to connect
    to a real Knowledge Graph Engine instance.
    """
    return MCPKGInquirer(
        logging.getLogger("tests.client_from_env"),
        endpoint_id=config_from_env.endpoint_id,
        part_id=config_from_env.part_id,
        api_key=config_from_env.api_key,
        base_url=config_from_env.base_url,
        timeout=config_from_env.timeout,
        max_retries=config_from_env.max_retries,
        retry_delay=config_from_env.retry_delay,
    )


# =============================================================================
# Integration Test Markers
# =============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires real server)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (uses mocks)"
    )
