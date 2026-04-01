"""Tests for MCPKGInquirer GraphQL module integration."""

import logging

from mcp_kg_inquirer import MCPKGInquirer


class TestGraphQLModuleIntegration:
    """Tests GraphQL module lookup on the client."""

    def test_get_graphql_module_builds_and_caches_module(self):
        """Test client builds module config from settings and caches it."""
        client = MCPKGInquirer(
            logging.getLogger("tests.graphql_module_integration"),
            endpoint_id="endpoint-1",
            part_id="part-1",
            api_key="secret",
            graphql_modules={
                "ai_kg_engine": {
                    "class_name": "Query",
                    "endpoint": "https://example.com/{endpoint_id}/graphql",
                    "x_api_key": "module-secret",
                }
            },
        )

        module = client.get_graphql_module("ai_kg_engine")
        same_module = client.get_graphql_module("ai_kg_engine")

        assert module is same_module
        assert module.endpoint_id == "endpoint-1"
        assert module.module_name == "ai_kg_engine"
        assert module.class_name == "Query"
        assert module.endpoint == "https://example.com/endpoint-1/graphql"
        assert module.x_api_key == "module-secret"
