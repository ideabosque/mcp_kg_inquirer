"""Tests for MCP configuration export."""

from mcp_kg_inquirer import MCP_CONFIGURATION


class TestMCPConfiguration:
    """Tests for MCP_CONFIGURATION."""

    def test_configuration_contains_expected_tools(self):
        """Test search and rag tools are exposed."""
        tool_names = [tool["name"] for tool in MCP_CONFIGURATION["tools"]]

        assert tool_names == ["search", "rag"]

    def test_configuration_points_to_inquirer_module(self):
        """Test module metadata points to this package."""
        module = MCP_CONFIGURATION["modules"][0]

        assert module["package_name"] == "mcp_kg_inquirer"
        assert module["module_name"] == "mcp_kg_inquirer"
        assert module["class_name"] == "MCPKGInquirer"
