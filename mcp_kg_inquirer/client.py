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
            "description": "Searches for information in the knowledge graph. Accepts a query text and optional filters to search across various data types. Returns relevant search results with pagination.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "Search query text",
                    },
                    "data_type": {
                        "type": "string",
                        "description": "Type of data to search (e.g., product, company, document)",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Additional filters for the search",
                    },
                    "similarity_search": {
                        "type": "boolean",
                        "description": "Enable similarity search",
                    },
                    "relevance_search": {
                        "type": "boolean",
                        "description": "Enable relevance search",
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results per page",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Additional prompt for search context",
                    },
                },
                "required": [],
            },
            "annotations": None,
        },
        {
            "name": "rag",
            "description": "Performs Retrieval-Augmented Generation (RAG) to answer questions based on the knowledge graph. Accepts a query text and optional prompt to generate contextually relevant answers using information retrieved from the knowledge graph.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "Query text for RAG",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Additional prompt for RAG context",
                    },
                },
                "required": [],
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
                "dataType": arguments.get("data_type"),
                "filters": arguments.get("filters"),
                "similaritySearch": arguments.get("similarity_search"),
                "relevanceSearch": arguments.get("relevance_search"),
                "page": arguments.get("page"),
                "limit": arguments.get("limit"),
                "prompt": arguments.get("prompt"),
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
