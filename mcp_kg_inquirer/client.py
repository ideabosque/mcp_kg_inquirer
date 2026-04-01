#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict

import httpx
import humps

from silvaengine_dynamodb_base.models import GraphqlSchemaModel
from silvaengine_utility.graphql import Graphql
from silvaengine_utility.serializer import Serializer

from .graphql_module import GraphQLModule

MCP_CONFIGURATION = {
    "tools": [
        {
            "name": "search",
            "description": "Searches for information in the knowledge graph using multiple search modes: vector (semantic similarity), text2cypher (LLM-generated Cypher), vector_cypher (vector + custom traversal), or hybrid (vector + fulltext).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "Search query text",
                    },
                    "search_mode": {
                        "type": "string",
                        "description": "Search mode: vector (semantic similarity), text2cypher (LLM generates Cypher), vector_cypher (vector + custom Cypher traversal), hybrid (vector + fulltext combined)",
                        "enum": ["vector", "text2cypher", "vector_cypher", "hybrid"],
                        "default": "text2cypher",
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Search type for categorizing search operations",
                    },
                    "index_name": {
                        "type": "string",
                        "description": "Vector index name",
                        "default": "vector",
                    },
                    "retrieval_query": {
                        "type": "string",
                        "description": "Custom Cypher retrieval query (used with vector_cypher mode)",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Additional filters for the search",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top results to retrieve",
                        "default": 10,
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination",
                        "default": 1,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results per page",
                        "default": 10,
                    },
                },
                "required": ["query_text"],
            },
            "annotations": None,
        },
        {
            "name": "rag",
            "description": "Performs Retrieval-Augmented Generation (RAG) to answer questions based on the knowledge graph. Supports vector (semantic search) and hybrid (vector + fulltext) retrieval modes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "Query text for RAG",
                    },
                    "search_mode": {
                        "type": "string",
                        "description": "Retriever mode: vector (semantic search) or hybrid (vector + fulltext)",
                        "enum": ["vector", "hybrid"],
                        "default": "vector",
                    },
                    "index_name": {
                        "type": "string",
                        "description": "Vector index name",
                        "default": "vector",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to retrieve for context",
                        "default": 5,
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Optional custom prompt template for RAG generation",
                    },
                },
                "required": ["query_text"],
            },
            "annotations": None,
        },
    ],
    "resources": [],
    "prompts": [],
    "module_links": [
        {
            "type": "tool",
            "name": "search",
            "module_name": "mcp_kg_inquirer",
            "class_name": "MCPKGInquirer",
            "function_name": "search",
            "return_type": "text",
        },
        {
            "type": "tool",
            "name": "rag",
            "module_name": "mcp_kg_inquirer",
            "class_name": "MCPKGInquirer",
            "function_name": "rag",
            "return_type": "text",
        },
    ],
    "modules": [
        {
            "package_name": "mcp_kg_inquirer",
            "module_name": "mcp_kg_inquirer",
            "class_name": "MCPKGInquirer",
            "setting": {
                "keyword": "knowledge_graph",
                "graphql_modules": {
                    "knowledge_graph_engine": {
                        "class_name": "KnowledgeGraphEngine",
                        "endpoint": "https://api.example.com/{endpoint_id}/knowledge_graph_graphql",
                        "x_api_key": "<api_key>",
                    },
                },
            },
        }
    ],
}


class MCPKGInquirer:
    def __init__(self, logger: logging.Logger, **setting: Dict[str, Any]):
        self.logger = logger
        self.setting = setting
        self._endpoint_id = None
        self._part_id = None
        self._graphql_modules = {}

    @property
    def endpoint_id(self) -> str | None:
        return self._endpoint_id

    @endpoint_id.setter
    def endpoint_id(self, value: str):
        self._endpoint_id = value

    @property
    def part_id(self) -> str | None:
        return self._part_id

    @part_id.setter
    def part_id(self, value: str):
        self._part_id = value

    def get_graphql_module(self, module_name: str) -> GraphQLModule | None:
        """Get a GraphQL module by name."""
        if not self._graphql_modules.get(module_name):
            self._graphql_modules[module_name] = GraphQLModule(
                endpoint_id=self.endpoint_id,
                module_name=module_name,
                class_name=self.setting.get("graphql_modules", {})
                .get(module_name, {})
                .get("class_name"),
                endpoint=self.setting.get("graphql_modules", {})
                .get(module_name, {})
                .get("endpoint"),
                x_api_key=self.setting.get("graphql_modules", {})
                .get(module_name, {})
                .get("x_api_key"),
            )

        return self._graphql_modules.get(module_name)

    def _execute_graphql_query(
        self,
        function_name: str,
        operation_name: str,
        operation_type: str,
        variables: Dict[str, Any],
        module_name: str = "knowledge_graph_engine",
    ) -> Dict[str, Any]:
        try:
            graphql_module = self.get_graphql_module(module_name)
            query = GraphqlSchemaModel.get_schema(
                endpoint_id=graphql_module.endpoint_id,
                operation_type=operation_type,
                operation_name=operation_name,
                module_name=module_name,
                enable_preferred_custom_schema=True,
            )

            if not query:
                query = Graphql.generate_graphql_operation(
                    operation_name, operation_type, graphql_module.schema
                )

            payload = Serializer.json_dumps({"query": query, "variables": variables})

            headers = {
                "x-api-key": graphql_module.x_api_key,
                "Part-Id": self.part_id,
                "Content-Type": "application/json",
            }

            with httpx.Client(http2=True, timeout=httpx.Timeout(30.0)) as client:
                response = client.post(
                    graphql_module.endpoint,
                    headers=headers,
                    content=payload,
                )

            result = response.json()

            if "errors" in result:
                error_message = result["errors"][0].get("message", "GraphQL error")
                raise Exception(f"GraphQL error: {error_message}")

            return result.get("data", {}).get(operation_name)
        except Exception as e:
            log = traceback.format_exc()
            self.logger.error(log)
            raise Exception(
                f"Failed to execute GraphQL query ({function_name}/{self.endpoint_id}). Error: {e}"
            )

    # * MCP Function.
    def search(self, **arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for information in the knowledge graph."""
        try:
            self.logger.info(f"Arguments: {arguments}")

            variables = {
                "queryText": arguments.get("query_text"),
                "searchMode": arguments.get("search_mode", "text2cypher"),
                "searchType": arguments.get("search_type"),
                "indexName": arguments.get("index_name", "vector"),
                "retrievalQuery": arguments.get("retrieval_query"),
                "filters": arguments.get("filters"),
                "topK": arguments.get("top_k", 10),
                "page": arguments.get("page", 1),
                "limit": arguments.get("limit", 10),
            }

            # Remove None values to avoid GraphQL validation errors
            variables = {k: v for k, v in variables.items() if v is not None}

            result = self._execute_graphql_query(
                "knowledge_graph_graphql",
                "search",
                "Query",
                variables,
            )

            return humps.decamelize(result)

        except Exception as e:
            log = traceback.format_exc()
            self.logger.error(log)
            raise e

    # * MCP Function.
    def rag(self, **arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Perform Retrieval-Augmented Generation (RAG) to answer questions."""
        try:
            self.logger.info(f"Arguments: {arguments}")

            variables = {
                "queryText": arguments.get("query_text"),
                "searchMode": arguments.get("search_mode", "vector"),
                "indexName": arguments.get("index_name", "vector"),
                "topK": arguments.get("top_k", 5),
                "prompt": arguments.get("prompt"),
            }

            # Remove None values to avoid GraphQL validation errors
            variables = {k: v for k, v in variables.items() if v is not None}

            result = self._execute_graphql_query(
                "knowledge_graph_graphql",
                "rag",
                "Query",
                variables,
            )

            return humps.decamelize(result)

        except Exception as e:
            log = traceback.format_exc()
            self.logger.error(log)
            raise e
