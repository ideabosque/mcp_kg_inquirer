"""Test configuration and fixtures for MCP KG Inquirer."""

import logging

import pytest

from mcp_kg_inquirer import MCPKGInquirer


@pytest.fixture
def client():
    """Create a test client."""
    client = MCPKGInquirer(
        logging.getLogger("tests.client"),
        keyword="knowledge_graph",
        graphql_modules={
            "knowledge_graph_engine": {
                "class_name": "AIKGEngine",
                "endpoint": "https://example.com/{endpoint_id}/ai_kg_engine_graphql",
                "x_api_key": "test-api-key",
            },
        },
    )
    client.endpoint_id = "test-endpoint"
    client.part_id = "test-partition"
    return client
