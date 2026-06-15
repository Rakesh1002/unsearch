"""
Database service.

This module re-exports the canonical implementation from app.services.core.database.
Tests and legacy imports continue to work while the production runtime uses the
same code path.
"""
from app.services.core.database import DatabaseService, get_database_service

__all__ = ["DatabaseService", "get_database_service"]
