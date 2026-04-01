"""Integration tests for MCP KG Inquirer."""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_kg_inquirer import Config
from mcp_kg_inquirer.client import CircuitBreaker
from mcp_kg_inquirer.exceptions import ConnectionError


class TestMCPKGInquirerIntegration:
    """Integration tests for MCPKGInquirer client."""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client, sample_health_response):
        """Test health check success."""
        with patch.object(client, "_post_graphql", AsyncMock(return_value=sample_health_response)):
            health = await client.health_check()
            
            assert health["healthy"] is True
            assert "endpoint" in health
            assert "circuit_breaker" in health
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client, sample_error_response):
        """Test health check failure."""
        with patch.object(client, "_post_graphql", AsyncMock(return_value=sample_error_response)):
            health = await client.health_check()
            
            assert health["healthy"] is False
            assert "error" in health
    
    @pytest.mark.asyncio
    async def test_batch_search(self, client, sample_search_response):
        """Test batch search."""
        with patch.object(client, "_post_graphql", AsyncMock(return_value=sample_search_response)):
            results = await client.batch_search(
                ["machine learning", "neural networks", "deep learning"]
            )
            
            assert len(results) == 3
            assert all(r.total == 2 for r in results)
    
    @pytest.mark.asyncio
    async def test_batch_rag(self, client, sample_rag_response):
        """Test batch RAG."""
        with patch.object(client, "_post_graphql", AsyncMock(return_value=sample_rag_response)):
            results = await client.batch_rag(
                ["What is AI?", "What is ML?", "What is DL?"],
                use_case="default",
            )
            
            assert len(results) == 3
            assert all(r.answer is not None for r in results)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, client):
        """Test circuit breaker opens after consecutive failures."""
        client.circuit_breaker.failure_threshold = 3
        with patch.object(
            client,
            "_post_graphql",
            AsyncMock(side_effect=ConnectionError("Connection refused")),
        ):
            # Make multiple failed requests
            for _ in range(3):
                try:
                    await client.search("test")
                except Exception:
                    pass
            
            # Circuit breaker should be open now
            assert client.circuit_breaker.is_open()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self, client, sample_search_response):
        """Test circuit breaker resets after successful request."""
        # First, open the circuit breaker
        client.circuit_breaker.state = "open"
        client.circuit_breaker.failure_count = 5
        with patch.object(client, "_post_graphql", AsyncMock(return_value=sample_search_response)):
            # Reset and make successful request
            client.circuit_breaker.reset()
            
            results = await client.search("test")
            
            assert client.circuit_breaker.is_closed()
            assert results.total == 2


class TestConfigIntegration:
    """Integration tests for Config."""
    
    def test_config_from_env_complete(self):
        """Test creating config from complete environment."""
        env_vars = {
            "KGE_ENDPOINT_ID": "test-endpoint",
            "KGE_PART_ID": "test-partition",
            "KGE_API_KEY": "test-key",
            "KGE_BASE_URL": "https://api.example.com",
            "KGE_TIMEOUT": "60.0",
            "KGE_MAX_RETRIES": "5",
        }
        
        with patch.dict("os.environ", env_vars, clear=False):
            config = Config.from_env()
            
            assert config.endpoint_id == "test-endpoint"
            assert config.part_id == "test-partition"
            assert config.api_key == "test-key"
            assert config.base_url == "https://api.example.com"
            assert config.timeout == 60.0
            assert config.max_retries == 5
    
    def test_config_graphql_endpoint_format(self):
        """Test GraphQL endpoint format."""
        config = Config(
            endpoint_id="prod-endpoint",
            part_id="tenant-1",
            api_key="secret",
            base_url="https://kg.example.com",
        )
        
        assert config.graphql_endpoint == "https://kg.example.com/prod-endpoint/knowledge_graph_graphql"
        assert config.partition_key == "prod-endpoint#tenant-1"


class TestCircuitBreakerIntegration:
    """Integration tests for CircuitBreaker."""
    
    def test_circuit_breaker_state_transitions(self):
        """Test circuit breaker state transitions."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        
        # Initial state: closed
        assert cb.is_closed()
        assert not cb.is_open()
        
        # Record failures
        cb.record_failure()
        cb.record_failure()
        assert cb.is_closed()  # Still closed, not enough failures
        
        # Third failure: opens
        cb.record_failure()
        assert cb.is_open()
        assert not cb.is_closed()
        
        # Reset
        cb.reset()
        assert cb.is_closed()
        assert not cb.is_open()
    
    def test_circuit_breaker_get_state(self):
        """Test getting circuit breaker state."""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        
        state = cb.get_state()
        
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["failure_threshold"] == 5
        assert state["recovery_timeout"] == 60.0
        assert state["last_failure_time"] is None
