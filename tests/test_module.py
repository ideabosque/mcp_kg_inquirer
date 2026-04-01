"""Tests for GraphQL module configuration."""

from mcp_kg_inquirer.graphql_module import GraphQLModule


class TestGraphQLModule:
    """Tests for GraphQLModule."""

    def test_init_formats_endpoint(self):
        """Test endpoint formatting during initialization."""
        module = GraphQLModule(
            endpoint_id="endpoint-1",
            endpoint="https://example.com/{endpoint_id}/graphql",
            x_api_key="secret",
        )

        assert module.endpoint_id == "endpoint-1"
        assert module.endpoint == "https://example.com/endpoint-1/graphql"
        assert module.x_api_key == "secret"
        assert module.module_name is None
        assert module.class_name is None
        assert module.schema is None

    def test_schema_lazy_load(self, monkeypatch):
        """Test schema is loaded lazily and cached."""
        calls = []

        def fake_get_graphql_schema(module_name, class_name):
            calls.append((module_name, class_name))
            return {"module": module_name, "class": class_name}

        monkeypatch.setattr(
            "mcp_kg_inquirer.graphql_module.Graphql.get_graphql_schema",
            staticmethod(fake_get_graphql_schema),
        )

        module = GraphQLModule(
            endpoint_id="endpoint-1",
            module_name="foo.bar",
            class_name="ExampleSchema",
        )

        assert module.schema == {"module": "foo.bar", "class": "ExampleSchema"}
        assert module.schema == {"module": "foo.bar", "class": "ExampleSchema"}
        assert calls == [("foo.bar", "ExampleSchema")]

    def test_refresh_schema_noop_without_module_and_class(self):
        """Test refresh_schema leaves schema unset when config is incomplete."""
        module = GraphQLModule(endpoint_id="endpoint-1")

        module.refresh_schema()

        assert module.schema is None
