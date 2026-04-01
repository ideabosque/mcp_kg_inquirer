"""Tests for MCPKGInquirer client."""

import logging
from unittest.mock import AsyncMock, patch

import pytest

from mcp_kg_inquirer import Config, MCPKGInquirer
from mcp_kg_inquirer.exceptions import (
    RAGError,
    SearchError,
)


class TestConfig:
    """Tests for Config class."""
    
    def test_config_creation(self):
        """Test creating a configuration."""
        config = Config(
            endpoint_id="test-endpoint",
            part_id="test-partition",
            api_key="test-api-key",
        )
        
        assert config.endpoint_id == "test-endpoint"
        assert config.part_id == "test-partition"
        assert config.api_key == "test-api-key"
        assert config.timeout == 30.0
        assert config.max_retries == 3
    
    def test_config_with_bearer_token(self):
        """Test creating a configuration with bearer token."""
        config = Config(
            endpoint_id="test-endpoint",
            part_id="test-partition",
            bearer_token="test-jwt-token",
        )
        
        assert config.endpoint_id == "test-endpoint"
        assert config.part_id == "test-partition"
        assert config.bearer_token == "test-jwt-token"
        assert config.api_key is None
    
    def test_config_headers_with_api_key(self):
        """Test headers with API key."""
        config = Config(
            endpoint_id="endpoint",
            part_id="partition",
            api_key="secret-key",
        )
        
        headers = config.headers
        assert headers["x-api-key"] == "secret-key"
        assert headers["Part-Id"] == "partition"
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers
    
    def test_config_headers_with_bearer_token(self):
        """Test headers with bearer token."""
        config = Config(
            endpoint_id="endpoint",
            part_id="partition",
            bearer_token="jwt-token",
        )
        
        headers = config.headers
        assert headers["Authorization"] == "Bearer jwt-token"
        assert headers["Part-Id"] == "partition"
        assert headers["Content-Type"] == "application/json"
        assert "x-api-key" not in headers
    
    def test_config_validation_missing_endpoint(self):
        """Test validation with missing endpoint_id."""
        with pytest.raises(ValueError):
            Config(endpoint_id="", part_id="test", api_key="key")
    
    def test_config_validation_missing_part(self):
        """Test validation with missing part_id."""
        with pytest.raises(ValueError):
            Config(endpoint_id="test", part_id="", api_key="key")
    
    def test_config_validation_missing_auth(self):
        """Test validation with missing authentication."""
        with pytest.raises(ValueError):
            Config(endpoint_id="test", part_id="test")
    
    def test_config_graphql_endpoint(self):
        """Test GraphQL endpoint property."""
        config = Config(
            endpoint_id="my-endpoint",
            part_id="my-partition",
            api_key="key",
            base_url="http://localhost:8000",
        )
        
        assert config.graphql_endpoint == "http://localhost:8000/my-endpoint/knowledge_graph_graphql"
    
    def test_config_partition_key(self):
        """Test partition key property."""
        config = Config(
            endpoint_id="endpoint",
            part_id="partition",
            api_key="key",
        )
        
        assert config.partition_key == "endpoint#partition"
    
    @patch.dict("os.environ", {
        "KGE_ENDPOINT_ID": "env-endpoint",
        "KGE_PART_ID": "env-partition",
        "KGE_API_KEY": "env-key",
    })
    def test_config_from_env_api_key(self):
        """Test creating config from environment with API key."""
        config = Config.from_env()
        
        assert config.endpoint_id == "env-endpoint"
        assert config.part_id == "env-partition"
        assert config.api_key == "env-key"
    
    @patch.dict("os.environ", {
        "KGE_ENDPOINT_ID": "env-endpoint",
        "KGE_PART_ID": "env-partition",
        "KGE_BEARER_TOKEN": "env-token",
    })
    def test_config_from_env_bearer_token(self):
        """Test creating config from environment with bearer token."""
        config = Config.from_env()
        
        assert config.endpoint_id == "env-endpoint"
        assert config.part_id == "env-partition"
        assert config.bearer_token == "env-token"
        assert config.api_key is None


class TestMCPKGInquirer:
    """Tests for MCPKGInquirer client."""
    
    def test_client_creation(self):
        """Test creating a client."""
        client = MCPKGInquirer(
            logging.getLogger("tests.test_client_creation"),
            endpoint_id="test-endpoint",
            part_id="test-partition",
            api_key="test-key",
        )
        
        assert client.config.endpoint_id == "test-endpoint"
        assert client.config.part_id == "test-partition"
        assert client.config.api_key == "test-key"
    
    @patch.dict("os.environ", {
        "KGE_ENDPOINT_ID": "env-endpoint",
        "KGE_PART_ID": "env-partition",
        "KGE_API_KEY": "env-key",
    })
    def test_client_from_env(self):
        """Test creating client from environment."""
        client = MCPKGInquirer.from_env(logging.getLogger("tests.test_client_from_env"))
        
        assert client.config.endpoint_id == "env-endpoint"
        assert client.config.part_id == "env-partition"
    
    @pytest.mark.asyncio
    async def test_close_client(self, client):
        """Test closing the client."""
        await client.close()
        # Should not raise any errors
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using client as async context manager."""
        async with MCPKGInquirer(
            logging.getLogger("tests.test_context_manager"),
            endpoint_id="test",
            part_id="test",
            api_key="test",
        ) as client:
            assert client is not None
        
        # Client should be closed after context exit
    
    @pytest.mark.asyncio
    async def test_search_vector(self, client, sample_search_response):
        """Test vector search."""
        with patch.object(client, "_post_graphql", AsyncMock(return_value=sample_search_response)):
            results = await client.search_vector("machine learning")
            
            assert results.total == 2
            assert len(results.results) == 2
            assert results.results[0].score == 0.95
    
    @pytest.mark.asyncio
    async def test_search_hybrid(self, client, sample_search_response):
        """Test hybrid search."""
        with patch.object(client, "_post_graphql", AsyncMock(return_value=sample_search_response)):
            results = await client.search_hybrid("machine learning")
            
            assert results.total == 2
            assert len(results.results) == 2
    
    @pytest.mark.asyncio
    async def test_rag(self, client, sample_rag_response):
        """Test RAG query."""
        with patch.object(client, "_post_graphql", AsyncMock(return_value=sample_rag_response)):
            response = await client.rag("What is machine learning?")
            
            assert response.answer is not None
            assert len(response.context) == 2
    
    @pytest.mark.asyncio
    async def test_search_error(self, client, sample_error_response):
        """Test search with error response."""
        with patch.object(client, "_post_graphql", AsyncMock(return_value=sample_error_response)):
            with pytest.raises(SearchError):
                await client.search("test query")
    
    @pytest.mark.asyncio
    async def test_rag_error(self, client, sample_error_response):
        """Test RAG with error response."""
        with patch.object(client, "_post_graphql", AsyncMock(return_value=sample_error_response)):
            with pytest.raises(RAGError):
                await client.rag("test question")
