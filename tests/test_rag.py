"""Tests for RAG module."""

import pytest

from mcp_kg_inquirer.exceptions import RAGError, ValidationError
from mcp_kg_inquirer.rag import (
    DEFAULT_PROMPT,
    EXPLANATION_PROMPT,
    SUMMARY_PROMPT,
    RAGContext,
    RAGRequest,
    RAGResponse,
    build_rag_request,
    get_prompt_for_use_case,
    parse_rag_response,
)


class TestRAGRequest:
    """Tests for RAGRequest."""
    
    def test_rag_request_creation(self):
        """Test creating a RAG request."""
        request = RAGRequest(
            query_text="What is machine learning?",
        )
        
        assert request.query_text == "What is machine learning?"
        assert request.top_k == 5
        assert request.similarity_threshold == 0.7
    
    def test_rag_request_validation_empty_query(self):
        """Test validation with empty query."""
        with pytest.raises(ValidationError):
            RAGRequest(query_text="")
    
    def test_rag_request_validation_invalid_top_k(self):
        """Test validation with invalid top_k."""
        with pytest.raises(ValidationError):
            RAGRequest(query_text="test", top_k=0)
        
        with pytest.raises(ValidationError):
            RAGRequest(query_text="test", top_k=100)
    
    def test_rag_request_validation_invalid_similarity(self):
        """Test validation with invalid similarity_threshold."""
        with pytest.raises(ValidationError):
            RAGRequest(query_text="test", similarity_threshold=-0.1)
        
        with pytest.raises(ValidationError):
            RAGRequest(query_text="test", similarity_threshold=1.5)
    
    def test_to_graphql_variables(self):
        """Test converting to GraphQL variables."""
        request = RAGRequest(
            query_text="test question",
            prompt="Custom prompt",
        )
        
        variables = request.to_graphql_variables()
        
        assert variables["queryText"] == "test question"
        assert variables["prompt"] == "Custom prompt"


class TestRAGContext:
    """Tests for RAGContext."""
    
    def test_rag_context_from_dict(self):
        """Test creating RAGContext from dictionary."""
        data = {
            "content": "Context content",
            "score": 0.92,
            "metadata": {"source": "wiki"},
            "source": "https://example.com",
        }
        
        context = RAGContext.from_dict(data)
        
        assert context.content == "Context content"
        assert context.score == 0.92
        assert context.metadata == {"source": "wiki"}
        assert context.source == "https://example.com"


class TestRAGResponse:
    """Tests for RAGResponse."""
    
    def test_rag_response_from_dict(self):
        """Test creating RAGResponse from dictionary."""
        data = {
            "answer": "Machine learning is AI subset.",
            "context": [
                {"content": "Context 1", "score": 0.9},
                {"content": "Context 2", "score": 0.8},
            ],
            "model": "gpt-4o",
            "latencyMs": 1500.0,
        }
        
        response = RAGResponse.from_dict(data)
        
        assert response.answer == "Machine learning is AI subset."
        assert len(response.context) == 2
        assert response.model == "gpt-4o"
        assert response.latency_ms == 1500.0


class TestBuildRAGRequest:
    """Tests for build_rag_request function."""
    
    def test_build_rag_request_basic(self):
        """Test building basic RAG request."""
        request = build_rag_request(query_text="test question")
        
        assert "query" in request
        assert "variables" in request
        assert request["variables"]["queryText"] == "test question"
    
    def test_build_rag_request_with_prompt(self):
        """Test building RAG request with custom prompt."""
        request = build_rag_request(
            query_text="test",
            prompt="Custom system prompt",
        )
        
        assert request["variables"]["prompt"] == "Custom system prompt"


class TestParseRAGResponse:
    """Tests for parse_rag_response function."""
    
    def test_parse_rag_response_success(self):
        """Test parsing successful response."""
        response = {
            "data": {
                "rag": {
                    "answer": "Test answer",
                    "context": [
                        {"content": "Context 1", "score": 0.9},
                    ],
                    "model": "gpt-4o",
                }
            }
        }
        
        result = parse_rag_response(response)
        
        assert result.answer == "Test answer"
        assert len(result.context) == 1
        assert result.model == "gpt-4o"
    
    def test_parse_rag_response_error(self):
        """Test parsing error response."""
        response = {
            "errors": [
                {"message": "RAG failed"}
            ]
        }
        
        with pytest.raises(RAGError):
            parse_rag_response(response)


class TestGetPromptForUseCase:
    """Tests for get_prompt_for_use_case function."""

    def test_default_prompt_contains_required_backend_placeholders(self):
        """Default prompt should satisfy backend template requirements."""
        for placeholder in ("{examples}", "{context}", "{query_text}"):
            assert placeholder in DEFAULT_PROMPT

    def test_summary_prompt_contains_required_backend_placeholders(self):
        """Summary prompt should satisfy backend template requirements."""
        for placeholder in ("{examples}", "{context}", "{query_text}"):
            assert placeholder in SUMMARY_PROMPT

    def test_explanation_prompt_contains_required_backend_placeholders(self):
        """Explanation prompt should satisfy backend template requirements."""
        for placeholder in ("{examples}", "{context}", "{query_text}"):
            assert placeholder in EXPLANATION_PROMPT
    
    def test_default_prompt(self):
        """Test getting default prompt."""
        prompt = get_prompt_for_use_case("default")
        assert prompt == DEFAULT_PROMPT
    
    def test_summary_prompt(self):
        """Test getting summary prompt."""
        prompt = get_prompt_for_use_case("summary")
        assert prompt == SUMMARY_PROMPT
    
    def test_explanation_prompt(self):
        """Test getting explanation prompt."""
        prompt = get_prompt_for_use_case("explanation")
        assert prompt == EXPLANATION_PROMPT
    
    def test_unknown_use_case(self):
        """Test getting prompt for unknown use case."""
        prompt = get_prompt_for_use_case("unknown")
        assert prompt == DEFAULT_PROMPT
