"""
Audit log endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from linuxpilot.audit.chain import AuditChain
from linuxpilot.config import settings

router = APIRouter()


class AuditVerifyResponse(BaseModel):
    valid: bool
    error: Optional[str] = None


class AuditEntryResponse(BaseModel):
    seq: int
    ts: str
    task: str
    step: Optional[str]
    kind: str
    payload: dict


@router.get("/{task_id}/verify", response_model=AuditVerifyResponse)
async def verify_audit(task_id: str):
    """Verify the integrity of an audit chain"""
    audit_chain = AuditChain(task_id)
    valid, error = audit_chain.verify()
    
    return AuditVerifyResponse(
        valid=valid,
        error=error,
    )


@router.get("/{task_id}/entries", response_model=List[AuditEntryResponse])
async def get_audit_entries(task_id: str, kind_filter: Optional[str] = None):
    """Get audit entries for a task"""
    audit_chain = AuditChain(task_id)
    entries = audit_chain.get_entries(kind_filter)
    
    return [
        AuditEntryResponse(
            seq=entry.seq,
            ts=entry.ts,
            task=entry.task,
            step=entry.step,
            kind=entry.kind,
            payload=entry.payload,
        )
        for entry in entries
    ]


@router.get("/{task_id}/final-hash")
async def get_final_hash(task_id: str):
    """Get the final hash of an audit chain"""
    audit_chain = AuditChain(task_id)
    final_hash = audit_chain.get_final_hash()
    
    if final_hash is None:
        raise HTTPException(status_code=404, detail="Audit chain not found")
    
    return {"hash": final_hash}
