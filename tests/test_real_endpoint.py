#!/usr/bin/env python3
"""Real endpoint tests for MCP KG Inquirer.

These tests perform actual HTTP requests to the Knowledge Graph Engine API.
Run with: python -m pytest tests/test_real_endpoint.py -v

Requires environment variables to be set in tests/.env:
- KGE_BASE_URL: The base URL of the Knowledge Graph Engine API
- KGE_ENDPOINT_ID: The endpoint ID
- KGE_PART_ID: The partition ID
- KGE_BEARER_TOKEN or KGE_API_KEY: Authentication credentials
"""

import json
import logging
import os
from pathlib import Path

import httpx
import pytest

# Load environment variables from tests/.env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestRealEndpoint:
    """Real endpoint tests against the Knowledge Graph Engine API."""

    @pytest.fixture(scope="class")
    def config(self):
        """Load configuration from environment variables."""
        config = {
            "base_url": os.environ.get("KGE_BASE_URL", "http://localhost:8000"),
            "endpoint_id": os.environ.get("KGE_ENDPOINT_ID", "test-endpoint"),
            "part_id": os.environ.get("KGE_PART_ID", "test-partition"),
            "api_key": os.environ.get("KGE_API_KEY"),
            "bearer_token": os.environ.get("KGE_BEARER_TOKEN"),
        }

        # Determine authentication method
        if config["bearer_token"]:
            config["auth_header"] = f"Bearer {config['bearer_token']}"
            config["auth_type"] = "bearer"
        elif config["api_key"]:
            config["auth_header"] = config["api_key"]
            config["auth_type"] = "api_key"
        else:
            pytest.skip("No authentication credentials provided. Set KGE_BEARER_TOKEN or KGE_API_KEY in tests/.env")

        return config

    @pytest.fixture(scope="class")
    def graphql_endpoint(self, config):
        """Construct the GraphQL endpoint URL."""
        return f"{config['base_url']}/{config['endpoint_id']}/knowledge_graph_graphql"

    @pytest.fixture(scope="class")
    def headers(self, config):
        """Construct request headers."""
        headers = {
            "Content-Type": "application/json",
            "Part-Id": config["part_id"],
        }

        if config["auth_type"] == "bearer":
            headers["Authorization"] = config["auth_header"]
        else:
            headers["x-api-key"] = config["auth_header"]

        return headers

    @pytest.fixture
    def client(self):
        """Create an HTTP client."""
        with httpx.Client(http2=True, timeout=httpx.Timeout(30.0)) as client:
            yield client

    def test_endpoint_connectivity(self, client, graphql_endpoint, headers):
        """Test basic connectivity to the GraphQL endpoint."""
        # Introspection query to check if endpoint is alive
        query = {
            "query": "{ __schema { queryType { name } } }"
        }

        response = client.post(
            graphql_endpoint,
            headers=headers,
            json=query
        )

        logger.info(f"Connectivity test status: {response.status_code}")
        assert response.status_code == 200, f"Endpoint returned status {response.status_code}: {response.text}"

        data = response.json()
        assert "data" in data or "errors" in data, f"Invalid GraphQL response: {data}"

    def test_search_endpoint(self, client, graphql_endpoint, headers):
        """Test the search operation on the real endpoint."""
        query = """
        query Search($queryText: String!, $limit: Int) {
            search(queryText: $queryText, limit: $limit) {
                results {
                    content
                    score
                    nodeId
                    labels
                }
                total
                page
                limit
            }
        }
        """

        variables = {
            "queryText": "machine learning",
            "limit": 5
        }

        payload = {
            "query": query,
            "variables": variables
        }

        logger.info(f"Testing search endpoint: {graphql_endpoint}")
        response = client.post(
            graphql_endpoint,
            headers=headers,
            json=payload
        )

        logger.info(f"Search response status: {response.status_code}")
        logger.info(f"Search response: {response.text[:500]}...")

        assert response.status_code == 200, f"Search failed with status {response.status_code}: {response.text}"

        data = response.json()
        assert "data" in data or "errors" in data, f"Invalid response: {data}"

        if "errors" in data:
            logger.warning(f"GraphQL errors: {data['errors']}")

        if "data" in data and data["data"] and "search" in data["data"]:
            search_result = data["data"]["search"]
            logger.info(f"Search returned {search_result.get('total', 0)} results")

    def test_rag_endpoint(self, client, graphql_endpoint, headers):
        """Test the RAG operation on the real endpoint."""
        query = """
        query RAG($queryText: String!, $prompt: String) {
            rag(queryText: $queryText, prompt: $prompt) {
                answer
                model
                latencyMs
                context {
                    content
                    score
                    source
                }
            }
        }
        """

        variables = {
            "queryText": "What is machine learning?",
            "prompt": "Be concise."
        }

        payload = {
            "query": query,
            "variables": variables
        }

        logger.info(f"Testing RAG endpoint: {graphql_endpoint}")
        response = client.post(
            graphql_endpoint,
            headers=headers,
            json=payload
        )

        logger.info(f"RAG response status: {response.status_code}")
        logger.info(f"RAG response: {response.text[:500]}...")

        assert response.status_code == 200, f"RAG failed with status {response.status_code}: {response.text}"

        data = response.json()
        assert "data" in data or "errors" in data, f"Invalid response: {data}"

        if "errors" in data:
            logger.warning(f"GraphQL errors: {data['errors']}")

        if "data" in data and data["data"] and "rag" in data["data"]:
            rag_result = data["data"]["rag"]
            logger.info(f"RAG answer: {rag_result.get('answer', 'N/A')[:100]}...")

    def test_search_with_filters(self, client, graphql_endpoint, headers):
        """Test search with filters on the real endpoint."""
        query = """
        query Search(
            $queryText: String!,
            $dataType: String,
            $filters: JSON,
            $page: Int,
            $limit: Int
        ) {
            search(
                queryText: $queryText,
                dataType: $dataType,
                filters: $filters,
                page: $page,
                limit: $limit
            ) {
                results {
                    content
                    score
                    nodeId
                    labels
                    metadata
                }
                total
                page
                limit
            }
        }
        """

        variables = {
            "queryText": "neural networks",
            "page": 1,
            "limit": 3
        }

        payload = {
            "query": query,
            "variables": variables
        }

        logger.info(f"Testing search with filters: {graphql_endpoint}")
        response = client.post(
            graphql_endpoint,
            headers=headers,
            json=payload
        )

        logger.info(f"Search with filters status: {response.status_code}")

        assert response.status_code == 200, f"Search failed with status {response.status_code}: {response.text}"

        data = response.json()
        assert "data" in data or "errors" in data, f"Invalid response: {data}"

        if "errors" in data:
            logger.warning(f"GraphQL errors: {data['errors']}")

    def test_error_handling_invalid_query(self, client, graphql_endpoint, headers):
        """Test error handling with an invalid query."""
        query = {
            "query": "{ invalidField }"
        }

        response = client.post(
            graphql_endpoint,
            headers=headers,
            json=query
        )

        logger.info(f"Invalid query test status: {response.status_code}")
        assert response.status_code == 200 or response.status_code == 400

        data = response.json()
        assert "errors" in data, "Expected errors for invalid query"
        logger.info(f"Error handling works correctly: {data['errors']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
