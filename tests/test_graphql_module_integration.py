"""Tests for MCPKGInquirer GraphQL module integration."""

import logging

from mcp_kg_inquirer import MCPKGInquirer


class TestGraphQLModuleIntegration:
    """Tests GraphQL module lookup on the client."""

    def test_get_graphql_module_builds_and_caches_module(self):
        """Test client builds module config from settings and caches it."""
        client = MCPKGInquirer(
            logging.getLogger("tests.graphql_module_integration"),
            graphql_modules={
                "knowledge_graph_engine": {
                    "class_name": "AIKGEngine",
                    "endpoint": "https://example.com/{endpoint_id}/ai_kg_engine_graphql",
                    "x_api_key": "module-secret",
                }
            },
        )
        client.endpoint_id = "endpoint-1"
        client.part_id = "part-1"

        module = client.get_graphql_module("knowledge_graph_engine")
        same_module = client.get_graphql_module("knowledge_graph_engine")

        assert module is same_module
        assert module.endpoint_id == "endpoint-1"
        assert module.module_name == "knowledge_graph_engine"
        assert module.class_name == "AIKGEngine"
        assert module.endpoint == "https://example.com/endpoint-1/ai_kg_engine_graphql"
        assert module.x_api_key == "module-secret"
