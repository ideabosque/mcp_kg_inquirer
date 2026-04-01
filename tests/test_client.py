"""Tests for MCPKGInquirer client."""

import logging
from unittest.mock import patch, MagicMock

import pytest

from mcp_kg_inquirer import MCPKGInquirer


class TestMCPKGInquirer:
    """Tests for MCPKGInquirer client."""

    def test_client_creation(self):
        """Test creating a client stores setting."""
        client = MCPKGInquirer(
            logging.getLogger("tests"),
            keyword="knowledge_graph",
            graphql_modules={
                "knowledge_graph_engine": {
                    "class_name": "AIKGEngine",
                    "endpoint": "https://example.com/{endpoint_id}/ai_kg_engine_graphql",
                    "x_api_key": "key",
                },
            },
        )

        assert client.endpoint_id is None
        assert client.part_id is None
        assert client.setting["keyword"] == "knowledge_graph"

    def test_endpoint_id_and_part_id_setters(self):
        """Test endpoint_id and part_id can be set via properties."""
        client = MCPKGInquirer(logging.getLogger("tests"))

        client.endpoint_id = "ep-1"
        client.part_id = "pt-1"

        assert client.endpoint_id == "ep-1"
        assert client.part_id == "pt-1"

    def test_search_delegates_to_graphql(self, client):
        """Test search builds variables and calls _execute_graphql_query."""
        mock_result = {"results": [], "total": 0}
        with patch.object(client, "_execute_graphql_query", return_value=mock_result) as mock_exec:
            result = client.search(query_text="machine learning", page=1, limit=5)

            mock_exec.assert_called_once_with(
                "ai_kg_engine_graphql",
                "search",
                "Query",
                {"queryText": "machine learning", "page": 1, "limit": 5},
            )

    def test_search_strips_none_variables(self, client):
        """Test search removes None values from variables."""
        mock_result = {"results": []}
        with patch.object(client, "_execute_graphql_query", return_value=mock_result) as mock_exec:
            client.search(query_text="test")

            call_variables = mock_exec.call_args[0][3]
            assert all(v is not None for v in call_variables.values())

    def test_rag_delegates_to_graphql(self, client):
        """Test rag builds variables and calls _execute_graphql_query."""
        mock_result = {"answer": "test answer"}
        with patch.object(client, "_execute_graphql_query", return_value=mock_result) as mock_exec:
            result = client.rag(query_text="What is AI?", prompt="Be concise.")

            mock_exec.assert_called_once_with(
                "ai_kg_engine_graphql",
                "rag",
                "Query",
                {"queryText": "What is AI?", "prompt": "Be concise."},
            )

    def test_rag_strips_none_variables(self, client):
        """Test rag removes None values from variables."""
        mock_result = {"answer": "test"}
        with patch.object(client, "_execute_graphql_query", return_value=mock_result) as mock_exec:
            client.rag(query_text="test")

            call_variables = mock_exec.call_args[0][3]
            assert "prompt" not in call_variables
