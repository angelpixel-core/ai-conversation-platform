"""Conformance test suite for Python 3.12+ strict typing and Google-style docstrings."""

import ast
import tomllib
from pathlib import Path

from src.application.conversations.commands.create_conversation import (
    CreateConversationCommandHandler,
)
from src.application.conversations.commands.send_message import (
    SendMessageCommandHandler,
)
from src.application.conversations.queries.stream_conversation import (
    StreamConversationQueryHandler,
)
from src.application.governance.commands.record_incident import (
    RecordSecurityIncidentCommandHandler,
)
from src.application.governance.queries.get_governance_metrics import (
    GetGovernanceMetricsQueryHandler,
)
from src.application.tenants.commands.provision_tenant_command import (
    ProvisionTenantCommandHandler,
)
from src.application.tenants.commands.reserve_quota_command import (
    ReserveQuotaCommandHandler,
)
from src.domain.agents.entities.workflow_instance import WorkflowInstance
from src.domain.conversations.entities.conversation import Conversation
from src.domain.governance.entities.security_incident import SecurityIncident
from src.domain.knowledge.entities.document import Document
from src.domain.tenants.entities.tenant import Tenant
from src.domain.tools.entities.tool_approval_request import ToolApprovalRequest


def test_no_legacy_typing_constructs_in_src() -> None:
    """Verifies that no Python source file in src/ imports deprecated typing constructs.

    Forbidden typing constructs: Union, Optional, List, Dict, Set, Tuple.
    In Python 3.12+, native types and | union operators must be used.
    """
    src_dir = Path("src")
    legacy_symbols = {"Union", "Optional", "List", "Dict", "Set", "Tuple"}
    violations: list[str] = []

    for py_file in src_dir.rglob("*.py"):
        # Ignore alembic migration scripts which use alembic templates
        if "migrations" in py_file.parts:
            continue

        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "typing":
                imported_names = {alias.name for alias in node.names}
                offending = imported_names.intersection(legacy_symbols)
                if offending:
                    violations.append(f"{py_file}: imports {offending} from typing")

    assert not violations, "Found legacy typing imports in src/:\n" + "\n".join(violations)


def test_core_aggregates_have_google_style_docstrings() -> None:
    """Verifies that all core aggregate roots have Google-style docstrings."""
    aggregates = [
        Conversation,
        Tenant,
        Document,
        WorkflowInstance,
        ToolApprovalRequest,
        SecurityIncident,
    ]

    for agg in aggregates:
        doc = agg.__doc__
        assert doc is not None and len(doc.strip()) > 10, (
            f"{agg.__name__} is missing class docstring"
        )

        # Verify create or append methods have Args: and Returns: or Raises:
        for method_name in ("create", "create_demo"):
            if hasattr(agg, method_name):
                method = getattr(agg, method_name)
                m_doc = method.__doc__
                assert m_doc is not None, f"{agg.__name__}.{method_name} is missing a docstring"
                assert "Args:" in m_doc, f"{agg.__name__}.{method_name} missing 'Args:' section"
                assert "Returns:" in m_doc, (
                    f"{agg.__name__}.{method_name} missing 'Returns:' section"
                )


def test_cqrs_handlers_have_google_style_docstrings() -> None:
    """Verifies that core CQRS handlers have Google-style docstrings on handle()."""
    handlers = [
        CreateConversationCommandHandler,
        SendMessageCommandHandler,
        StreamConversationQueryHandler,
        ProvisionTenantCommandHandler,
        ReserveQuotaCommandHandler,
        RecordSecurityIncidentCommandHandler,
        GetGovernanceMetricsQueryHandler,
    ]

    for handler_cls in handlers:
        handle_method = getattr(handler_cls, "handle", None)
        assert handle_method is not None, f"{handler_cls.__name__} has no handle method"
        doc = handle_method.__doc__
        assert doc is not None, f"{handler_cls.__name__}.handle is missing a docstring"
        assert "Args:" in doc, f"{handler_cls.__name__}.handle missing 'Args:' section"
        assert "Returns:" in doc, f"{handler_cls.__name__}.handle missing 'Returns:' section"


def test_pyright_configuration_strictness() -> None:
    """Verifies pyproject.toml has standard typeCheckingMode and strict diagnostics."""
    pyproject_path = Path("pyproject.toml")
    assert pyproject_path.exists(), "pyproject.toml not found"

    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    pyright_cfg = data.get("tool", {}).get("pyright", {})
    assert pyright_cfg.get("typeCheckingMode") == "standard"
    assert pyright_cfg.get("reportAssertAlwaysTrue") == "error"
    assert pyright_cfg.get("reportSelfClsParameterName") == "error"
    assert pyright_cfg.get("reportConstantRedefinition") == "error"
    assert pyright_cfg.get("reportDuplicateImport") == "error"
