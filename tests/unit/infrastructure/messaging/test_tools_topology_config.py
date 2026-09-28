"""Unit tests for ToolsTopologyConfig."""

from src.infrastructure.messaging.rabbitmq.tools_topology_config import (
    ToolsTopologyConfig,
)


def test_tools_topology_config_defaults() -> None:
    config = ToolsTopologyConfig()

    assert config.exchange_name == "ai_platform.tools"
    assert config.queue_name == "tools.execution.queue"
    assert config.dlx_exchange_name == "ai_platform.tools.dlx"
    assert config.dlq_name == "tools.execution.dlq"
    assert config.routing_key == "tools.execute"
    assert config.tenant_routing_pattern == "tenant.*.tools.execute"


def test_tools_topology_format_tenant_routing_key() -> None:
    config = ToolsTopologyConfig()

    key = config.format_tenant_routing_key("corp-acme", "execute")
    assert key == "tenant.corp-acme.tools.execute"

    custom_key = config.format_tenant_routing_key("corp-acme", "approved")
    assert custom_key == "tenant.corp-acme.tools.approved"
