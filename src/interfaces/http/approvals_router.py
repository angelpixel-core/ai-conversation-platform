"""Expose approvals_router at interfaces/http level as specified in roadmap."""

from src.interfaces.http.routers.approvals_router import create_approvals_router

__all__ = ["create_approvals_router"]
