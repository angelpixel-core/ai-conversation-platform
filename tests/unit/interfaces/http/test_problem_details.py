"""Unit tests for RFC 7807 Problem Details and interface schemas conformance."""

from uuid import uuid4

from fastapi.testclient import TestClient

from src.domain.governance.exceptions import SafetyPolicyViolationError
from src.interfaces.http.agents_schemas import (
    AgentActivityEventSchema,
)
from src.interfaces.http.api import build_api
from src.interfaces.http.knowledge_schemas import (
    CitationSchema,
)
from src.interfaces.http.problem_details import (
    ProblemDetails,
    problem_details_response,
)


def test_problem_details_model__minimal_fields() -> None:
    """Verifies ProblemDetails instantiation with baseline RFC 7807 fields."""
    pd = ProblemDetails(
        title="Invalid Request",
        status=400,
        detail="Payload validation failed.",
    )
    assert pd.type == "about:blank"
    assert pd.title == "Invalid Request"
    assert pd.status == 400
    assert pd.detail == "Payload validation failed."
    assert pd.code is None
    assert pd.error is None
    assert pd.message is None


def test_problem_details_model__full_fields_and_extensions() -> None:
    """Verifies ProblemDetails serialization with full fields and extra extensions."""
    pd = ProblemDetails(
        type="urn:problem:safety-policy-violation",
        title="Safety Policy Violation",
        status=400,
        detail="Prompt injection detected.",
        code="PROMPT_INJECTION_DETECTED",
        error="SafetyPolicyViolation",
        message="Prompt injection detected.",
        incident_id="inc-999",
    )
    assert pd.type == "urn:problem:safety-policy-violation"
    assert pd.code == "PROMPT_INJECTION_DETECTED"
    data = pd.model_dump()
    assert data["incident_id"] == "inc-999"


def test_problem_details_response_factory__returns_problem_json_media_type() -> None:
    """Verifies factory sets application/problem+json and expected keys."""
    resp = problem_details_response(
        status_code=409,
        title="Idempotency Conflict",
        detail="Request with key already in flight.",
        type_uri="urn:problem:idempotency-conflict",
        code="IDEMPOTENCY_CONFLICT",
    )
    assert resp.status_code == 409
    assert resp.headers["content-type"] == "application/problem+json"

    import json

    body = json.loads(bytes(resp.body).decode("utf-8"))
    assert body["type"] == "urn:problem:idempotency-conflict"
    assert body["title"] == "Idempotency Conflict"
    assert body["status"] == 409
    assert body["detail"] == "Request with key already in flight."
    assert body["code"] == "IDEMPOTENCY_CONFLICT"
    assert body["error"] == "IDEMPOTENCY_CONFLICT"
    assert body["message"] == "Request with key already in flight."


def test_problem_details_response_factory__merges_extensions() -> None:
    """Verifies custom keyword arguments are included as extension members."""
    resp = problem_details_response(
        status_code=400,
        title="Safety Violation",
        detail="Blocked instruction override.",
        violation_type="PROMPT_INJECTION",
        risk_score=0.98,
        matched_rule="INSTRUCTION_OVERRIDE",
        incident_id="inc-42",
    )
    import json

    body = json.loads(bytes(resp.body).decode("utf-8"))
    assert body["violation_type"] == "PROMPT_INJECTION"
    assert body["risk_score"] == 0.98
    assert body["matched_rule"] == "INSTRUCTION_OVERRIDE"
    assert body["incident_id"] == "inc-42"


def test_api_exception_handler__safety_policy_violation() -> None:
    """Verifies exception handler serializes SafetyPolicyViolationError with RFC 7807."""
    app = build_api()

    # Route that triggers SafetyPolicyViolationError for testing handler
    @app.get("/test-safety-trigger")
    def trigger_safety() -> None:
        raise SafetyPolicyViolationError(
            message="Malicious jailbreak attempt.",
            violation_type="PROMPT_INJECTION",
            risk_score=0.99,
            matched_rule="OVERRIDE_DIRECTIVE",
            incident_id="inc-test-01",
        )

    client = TestClient(app)
    response = client.get("/test-safety-trigger")

    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["type"] == "urn:problem:safety-policy-violation"
    assert data["title"] == "Safety Policy Violation"
    assert data["status"] == 400
    assert data["code"] == "PROMPT_INJECTION_DETECTED"
    assert data["error"] == "SafetyPolicyViolation"
    assert data["message"] == "Malicious jailbreak attempt."
    assert data["violation_type"] == "PROMPT_INJECTION"
    assert data["risk_score"] == 0.99
    assert data["matched_rule"] == "OVERRIDE_DIRECTIVE"
    assert data["incident_id"] == "inc-test-01"


def test_api_exception_handler__conversation_not_found() -> None:
    """Verifies exception handler serializes ConversationNotFoundError with RFC 7807."""
    app = build_api()

    from src.domain.conversations.exceptions import ConversationNotFoundError

    @app.get("/test-not-found-trigger")
    def trigger_not_found() -> None:
        conv_id = uuid4()
        raise ConversationNotFoundError(conv_id)

    client = TestClient(app)
    response = client.get("/test-not-found-trigger")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["type"] == "urn:problem:conversation-not-found"
    assert data["title"] == "Conversation Not Found"
    assert data["status"] == 404
    assert data["code"] == "CONVERSATION_NOT_FOUND"


def test_schemas_conformance() -> None:
    """Verifies Pydantic v2 DTO schemas instantiate correctly."""
    citation = CitationSchema(
        source_document_id="doc-1",
        document_name="guide.pdf",
        chunk_id="chunk-1",
        similarity_score=0.95,
        snippet="test text",
    )
    assert citation.source_document_id == "doc-1"
    event = AgentActivityEventSchema(event_type="test", data={"k": "v"})
    assert event.event_type == "test"
