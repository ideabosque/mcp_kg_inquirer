"""Integration tests for MCP KG Inquirer."""

import logging
from unittest.mock import patch

import pytest

from mcp_kg_inquirer import MCPKGInquirer


class TestMCPKGInquirerIntegration:
    """Integration tests for MCPKGInquirer client."""

    def test_get_graphql_module_uses_endpoint_id(self):
        """Test GraphQL module formats endpoint with endpoint_id."""
        client = MCPKGInquirer(
            logging.getLogger("tests"),
            graphql_modules={
                "knowledge_graph_engine": {
                    "class_name": "AIKGEngine",
                    "endpoint": "https://api.example.com/{endpoint_id}/ai_kg_engine_graphql",
                    "x_api_key": "secret",
                },
            },
        )
        client.endpoint_id = "prod-endpoint"
        client.part_id = "tenant-1"

        module = client.get_graphql_module("knowledge_graph_engine")

        assert module.endpoint == "https://api.example.com/prod-endpoint/ai_kg_engine_graphql"
        assert module.x_api_key == "secret"
        assert module.endpoint_id == "prod-endpoint"

    def test_get_graphql_module_missing_returns_empty(self):
        """Test getting a non-configured module returns module with None values."""
        client = MCPKGInquirer(
            logging.getLogger("tests"),
            graphql_modules={},
        )
        client.endpoint_id = "ep-1"

        module = client.get_graphql_module("nonexistent")

        assert module.endpoint is None
        assert module.x_api_key is None
