"""AST conformance guard test ensuring 0 backward-compatibility aliases exist in src/."""

import ast
from pathlib import Path

FORBIDDEN_EXACT_ALIASES = {
    "UnitOfWork",
    "EventPublisher",
    "HttpClient",
    "ConversationRepository",
    "InMemoryUnitOfWork",
    "MssqlUnitOfWork",
    "AnyioSandboxedToolRunner",
    "AnyioStreamGuardrailFilter",
    "InMemoryMessageBroker",
    "OutboxDispatcher",
    "InMemoryOutboxRepository",
    "HttpxClient",
    "HttpxClientAdapter",
    "RabbitMqPublisherAdapter",
    "RabbitMqEventPublisherAdapter",
    "RabbitMqConsumerAdapter",
    "RabbitMqEventConsumerAdapter",
}

LEGACY_CQRS_SUFFIXES = ("CommandHandler", "QueryHandler")


def _is_legacy_cqrs_alias(name: str, value_node: ast.expr) -> bool:
    """Check if an assignment targets *Handler where value is *CommandHandler or *QueryHandler."""
    if not name.endswith("Handler") or name.endswith(("CommandHandler", "QueryHandler")):
        return False
    if name.endswith(("AsyncCommandHandler", "AsyncQueryHandler")):
        return False
    return isinstance(value_node, ast.Name) and value_node.id.endswith(LEGACY_CQRS_SUFFIXES)


def _check_file_ast(py_file: Path, src_dir: Path) -> list[str]:
    """Inspect AST of a Python file for forbidden legacy assignments."""
    rel = py_file.relative_to(src_dir)
    content = py_file.read_text(encoding="utf-8")
    violations: list[str] = []

    if "# Alias for backward compatibility" in content:
        violations.append(f"{rel}: contains '# Alias for backward compatibility'")

    try:
        tree = ast.parse(content, filename=str(py_file))
    except SyntaxError as e:
        return [f"{rel}: SyntaxError {e}"]

    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign):
            continue
        for target in stmt.targets:
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            if name in FORBIDDEN_EXACT_ALIASES:
                violations.append(f"{rel}:{stmt.lineno}: forbidden alias '{name}'")
            elif name.endswith("DataMapper"):
                violations.append(f"{rel}:{stmt.lineno}: legacy DataMapper '{name}'")
            elif _is_legacy_cqrs_alias(name, stmt.value):
                violations.append(f"{rel}:{stmt.lineno}: legacy CQRS alias '{name}'")

    return violations


def test_no_backward_compatibility_aliases_in_src() -> None:
    """Verifies that no legacy backward-compatibility aliases are declared in src/."""
    src_dir = Path(__file__).resolve().parents[3] / "src"
    violations: list[str] = []

    for py_file in src_dir.rglob("*.py"):
        violations.extend(_check_file_ast(py_file, src_dir))

    msg = "Found legacy backward-compatibility aliases in src/:\n" + "\n".join(violations)
    assert not violations, msg
