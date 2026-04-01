"""
RAG (Retrieval-Augmented Generation) implementation for MCP KG Inquirer.

Provides question-answering capabilities using GraphRAG to retrieve
context from the knowledge graph and generate answers.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mcp_kg_inquirer.exceptions import RAGError, ValidationError


@dataclass
class RAGRequest:
    """RAG request parameters.

    Attributes:
        query_text: The question to answer.
        prompt: Optional custom system prompt template.
        top_k: Number of context documents to retrieve (default: 5).
        similarity_threshold: Minimum similarity score for context (default: 0.7).
    """

    query_text: str
    prompt: Optional[str] = None
    top_k: int = 5
    similarity_threshold: float = 0.7

    def __post_init__(self):
        """Validate request parameters."""
        if not self.query_text or not self.query_text.strip():
            raise ValidationError("query_text is required and cannot be empty")

        if self.top_k < 1 or self.top_k > 50:
            raise ValidationError("top_k must be between 1 and 50")

        if self.similarity_threshold < 0 or self.similarity_threshold > 1:
            raise ValidationError("similarity_threshold must be between 0 and 1")

    def to_graphql_variables(self) -> Dict[str, Any]:
        """Convert request to GraphQL variables.

        Returns:
            Dictionary of GraphQL variables.
        """
        variables = {
            "queryText": self.query_text,
        }

        if self.prompt:
            variables["prompt"] = self.prompt

        return variables


@dataclass
class RAGContext:
    """RAG context item.

    Attributes:
        content: The content of the context document.
        score: The relevance score.
        metadata: Additional metadata.
        source: The source of the context.
    """

    content: str
    score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    source: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RAGContext":
        """Create a RAGContext from a dictionary.

        Args:
            data: The context dictionary.

        Returns:
            A RAGContext instance.
        """
        return cls(
            content=data.get("content", ""),
            score=data.get("score", 0.0),
            metadata=data.get("metadata"),
            source=data.get("source"),
        )


@dataclass
class RAGResponse:
    """RAG response.

    Attributes:
        answer: The generated answer text.
        context: List of context items used for generation.
        model: The LLM model used for generation.
        latency_ms: Generation latency in milliseconds.
    """

    answer: str = ""
    context: List[RAGContext] = field(default_factory=list)
    model: Optional[str] = None
    latency_ms: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RAGResponse":
        """Create a RAGResponse from a dictionary.

        Args:
            data: The response dictionary.

        Returns:
            A RAGResponse instance.
        """
        context_data = data.get("context", [])
        context = [RAGContext.from_dict(c) for c in context_data]

        return cls(
            answer=data.get("answer", ""),
            context=context,
            model=data.get("model"),
            latency_ms=data.get("latencyMs") or data.get("latency_ms"),
        )


# GraphQL query for RAG
RAG_QUERY = """
query RAG($queryText: String!, $searchMode: String, $indexName: String, $topK: Int, $prompt: String) {
  rag(queryText: $queryText, searchMode: $searchMode, indexName: $indexName, topK: $topK, prompt: $prompt) {
    answer
    context
    sources
  }
}
"""


# Default system prompts for different use cases
DEFAULT_PROMPT = """You are a helpful assistant that answers questions using the provided knowledge graph retrieval results.

Examples:
{examples}

Context:
{context}

Question:
{query_text}

Answer using only the provided context. If the answer is not present, say so clearly.
Be concise and accurate."""

SUMMARY_PROMPT = """You are a summarization assistant.

Examples:
{examples}

Context:
{context}

Question:
{query_text}

Provide a clear, concise summary grounded only in the provided context.
Focus on the key points and organize the response logically."""

EXPLANATION_PROMPT = """You are an explanation assistant.

Examples:
{examples}

Context:
{context}

Question:
{query_text}

Explain the answer clearly using only the provided context.
Use simple language and break down complex ideas when helpful."""


def build_rag_request(
    query_text: str,
    prompt: Optional[str] = None,
    top_k: int = 5,
    similarity_threshold: float = 0.7,
) -> Dict[str, Any]:
    """Build a GraphQL RAG request.

    Args:
        query_text: The question to answer.
        prompt: Optional custom system prompt.
        top_k: Number of context documents to retrieve.
        similarity_threshold: Minimum similarity score.

    Returns:
        Dictionary with query and variables for GraphQL request.

    Raises:
        ValidationError: If parameters are invalid.
    """
    request = RAGRequest(
        query_text=query_text,
        prompt=prompt,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
    )

    variables = request.to_graphql_variables()

    return {
        "query": RAG_QUERY,
        "variables": variables,
    }


def parse_rag_response(response: Dict[str, Any]) -> RAGResponse:
    """Parse a GraphQL RAG response.

    Args:
        response: The raw GraphQL response.

    Returns:
        A RAGResponse instance.

    Raises:
        RAGError: If the response indicates an error.
    """
    if "errors" in response:
        errors = response.get("errors", [])
        error_msg = errors[0].get("message", "Unknown error") if errors else "Unknown error"
        raise RAGError(f"GraphQL error: {error_msg}", {"errors": errors})

    data = response.get("data", {})
    rag_data = data.get("rag", {})

    return RAGResponse.from_dict(rag_data)


def get_prompt_for_use_case(use_case: str) -> str:
    """Get a default prompt for a specific use case.

    Args:
        use_case: The use case identifier (default, summary, explanation).

    Returns:
        The appropriate prompt template.
    """
    prompts = {
        "default": DEFAULT_PROMPT,
        "summary": SUMMARY_PROMPT,
        "explanation": EXPLANATION_PROMPT,
    }

    return prompts.get(use_case, DEFAULT_PROMPT)
