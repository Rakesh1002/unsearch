"""
Audit API - per-API-key retrieval audit log.

Every verified search, extract, and citation has an event record that includes
references to the signed citation envelopes produced. This supports compliance
workflows such as EU AI Act Article 12 logging.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.dependencies import AuthUserDep, CitationStoreDep
from app.services.citation_store import CitationStore

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditListParams(BaseModel):
    """Query parameters for audit log listing."""
    start_date: Optional[datetime] = Field(default=None, description="ISO 8601 start of range")
    end_date: Optional[datetime] = Field(default=None, description="ISO 8601 end of range")
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditLogResponse(BaseModel):
    """Paginated audit log response."""
    api_key_id: Optional[str]
    total: int
    limit: int
    offset: int
    events: list


@router.get("", response_model=AuditLogResponse)
async def get_audit_log(
    auth_user: AuthUserDep,
    citation_store: CitationStoreDep,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    Retrieve the audit log for the authenticated API key.

    Returns citation-envelope references for every retrieval made under this key,
    newest first. Date filtering is optional.
    """
    if not auth_user or not auth_user.api_key_id:
        raise HTTPException(status_code=401, detail="API key required")

    events = await citation_store.get_audit_events(
        api_key_id=auth_user.api_key_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    return AuditLogResponse(
        api_key_id=auth_user.api_key_id,
        total=len(events),
        limit=limit,
        offset=offset,
        events=events,
    )


async def record_audit_event(
    citation_store: CitationStore,
    api_key_id: Optional[str],
    request_id: str,
    endpoint: str,
    results: list,
):
    """Background helper: record an audit event with envelope references."""
    if not api_key_id:
        return
    refs = []
    for r in results:
        env = getattr(r, "citation_envelope", None) or getattr(r, "envelope", None)
        if env:
            env_dict = env.model_dump() if hasattr(env, "model_dump") else env.dict()
            refs.append(
                {
                    "url": env_dict.get("url"),
                    "snapshot_key": env_dict.get("snapshot_key"),
                    "content_sha256": env_dict.get("content_sha256"),
                    "signed_at": env_dict.get("signed_at"),
                }
            )
    try:
        await citation_store.log_audit_event(
            api_key_id=api_key_id,
            request_id=request_id,
            endpoint=endpoint,
            envelope_refs=refs,
        )
    except Exception:
        # Audit logging must never fail the request.
        pass
