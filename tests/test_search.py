"""Tests for search module."""

import pytest

from mcp_kg_inquirer.exceptions import SearchError, ValidationError
from mcp_kg_inquirer.search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    build_search_request,
    parse_search_response,
)


class TestSearchRequest:
    """Tests for SearchRequest."""
    
    def test_search_request_creation(self):
        """Test creating a search request."""
        request = SearchRequest(
            query_text="machine learning",
            page=1,
            limit=10,
        )
        
        assert request.query_text == "machine learning"
        assert request.page == 1
        assert request.limit == 10
    
    def test_search_request_validation_empty_query(self):
        """Test validation with empty query."""
        with pytest.raises(ValidationError):
            SearchRequest(query_text="")
    
    def test_search_request_validation_invalid_page(self):
        """Test validation with invalid page."""
        with pytest.raises(ValidationError):
            SearchRequest(query_text="test", page=0)
    
    def test_search_request_validation_invalid_limit(self):
        """Test validation with invalid limit."""
        with pytest.raises(ValidationError):
            SearchRequest(query_text="test", limit=0)
        
        with pytest.raises(ValidationError):
            SearchRequest(query_text="test", limit=200)
    
    def test_to_graphql_variables(self):
        """Test converting to GraphQL variables."""
        request = SearchRequest(
            query_text="test query",
            similarity_search=True,
            page=1,
            limit=5,
        )
        
        variables = request.to_graphql_variables()
        
        assert variables["queryText"] == "test query"
        assert variables["searchMode"] == "vector"
        assert variables["page"] == 1
        assert variables["limit"] == 5
    
    def test_to_graphql_variables_hybrid(self):
        """Test converting to GraphQL variables with hybrid mode."""
        request = SearchRequest(
            query_text="test query",
            relevance_search=True,
        )
        
        variables = request.to_graphql_variables()
        
        assert variables["searchMode"] == "hybrid"


class TestSearchResult:
    """Tests for SearchResult."""
    
    def test_search_result_from_dict(self):
        """Test creating SearchResult from dictionary."""
        data = {
            "content": "Test content",
            "score": 0.95,
            "metadata": {"source": "wiki"},
            "node_id": "node-001",
            "labels": ["Concept"],
        }
        
        result = SearchResult.from_dict(data)
        
        assert result.content == "Test content"
        assert result.score == 0.95
        assert result.metadata == {"source": "wiki"}
        assert result.node_id == "node-001"
        assert result.labels == ["Concept"]


class TestSearchResponse:
    """Tests for SearchResponse."""
    
    def test_search_response_from_dict(self):
        """Test creating SearchResponse from dictionary."""
        data = {
            "results": [
                {"content": "Result 1", "score": 0.9},
                {"content": "Result 2", "score": 0.8},
            ],
            "total": 2,
            "page": 1,
            "limit": 10,
        }
        
        response = SearchResponse.from_dict(data)
        
        assert response.total == 2
        assert len(response.results) == 2
        assert response.page == 1
        assert response.limit == 10
        assert response.results[0].content == "Result 1"
        assert response.results[1].score == 0.8


class TestBuildSearchRequest:
    """Tests for build_search_request function."""
    
    def test_build_search_request_basic(self):
        """Test building basic search request."""
        request = build_search_request(query_text="test")
        
        assert "query" in request
        assert "variables" in request
        assert request["variables"]["queryText"] == "test"
    
    def test_build_search_request_with_mode(self):
        """Test building search request with explicit mode."""
        request = build_search_request(
            query_text="test",
            search_mode="hybrid",
        )
        
        assert request["variables"]["searchMode"] == "hybrid"
    
    def test_build_search_request_with_filters(self):
        """Test building search request with filters."""
        request = build_search_request(
            query_text="test",
            filters={"category": "AI"},
        )
        
        assert request["variables"]["filters"] == {"category": "AI"}


class TestParseSearchResponse:
    """Tests for parse_search_response function."""
    
    def test_parse_search_response_success(self):
        """Test parsing successful response."""
        response = {
            "data": {
                "search": {
                    "results": [{"content": "Test", "score": 0.9}],
                    "total": 1,
                    "page": 1,
                    "limit": 10,
                }
            }
        }
        
        result = parse_search_response(response)
        
        assert result.total == 1
        assert len(result.results) == 1
    
    def test_parse_search_response_error(self):
        """Test parsing error response."""
        response = {
            "errors": [
                {"message": "Something went wrong"}
            ]
        }
        
        with pytest.raises(SearchError):
            parse_search_response(response)
