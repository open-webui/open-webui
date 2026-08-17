from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from open_webui.utils.auth import get_admin_user, get_verified_user
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

router = APIRouter()

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


class ToolTier(str, Enum):
    READ_ONLY = "read_only"
    MUTATING = "mutating"
    DESTRUCTIVE = "destructive"
    ADMIN = "admin"


class GateDecision(str, Enum):
    ALLOWED = "allowed"
    REJECTED = "rejected"
    SIMULATED = "simulated"
    CONFIRMATION_REQUIRED = "confirmation_required"


class ActionVerificationRequest(BaseModel):
    tool_name: str
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    tool_tier: ToolTier = ToolTier.MUTATING
    user_confirmed: bool = False
    prove_token: Optional[str] = None
    simulation_mode: bool = False


class ActionVerificationResponse(BaseModel):
    decision: GateDecision
    allowed: bool
    reason: str
    action_id: str
    current_hash: str
    timestamp: str


class ActionLedgerEntry(BaseModel):
    index: int
    action_id: str
    timestamp: str
    tool_name: str
    tool_tier: str
    decision: str
    prev_hash: str
    curr_hash: str


class ActionGateLedger:
    def __init__(self):
        self._entries: List[Dict[str, Any]] = []
        self._last_hash = GENESIS_HASH

    def record_action(
        self,
        action_id: str,
        tool_name: str,
        tool_tier: ToolTier,
        decision: GateDecision,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        index = len(self._entries)

        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        canonical_content = f"{index}|{self._last_hash}|{action_id}|{tool_name}|{tool_tier.value}|{decision.value}|{timestamp}|{hashlib.sha256(payload_bytes).hexdigest()}"
        curr_hash = hashlib.sha256(canonical_content.encode("utf-8")).hexdigest()

        entry = {
            "index": index,
            "action_id": action_id,
            "timestamp": timestamp,
            "tool_name": tool_name,
            "tool_tier": tool_tier.value,
            "decision": decision.value,
            "prev_hash": self._last_hash,
            "curr_hash": curr_hash,
        }

        self._entries.append(entry)
        self._last_hash = curr_hash
        return entry

    def get_entries(self) -> List[Dict[str, Any]]:
        return list(self._entries)

    def verify_integrity(self) -> bool:
        prev = GENESIS_HASH
        for entry in self._entries:
            if entry["prev_hash"] != prev:
                return False
            prev = entry["curr_hash"]
        return True


# Global in-memory ActionGate state
GLOBAL_ACTION_LEDGER = ActionGateLedger()


def check_kill_switch_active() -> bool:
    if os.environ.get("AAG_KILL_SWITCH", "").lower() in ("true", "1", "yes"):
        return True
    kill_paths = [Path("artifacts/KILL"), Path("/tmp/KILL")]
    return any(p.exists() for p in kill_paths)


@router.get("/status")
async def get_action_gate_status(user=Depends(get_verified_user)):
    """
    Returns the current status of the ActionGate security boundary.
    """
    kill_active = check_kill_switch_active()
    ledger_entries = GLOBAL_ACTION_LEDGER.get_entries()
    is_valid = GLOBAL_ACTION_LEDGER.verify_integrity()

    return {
        "status": "active" if not kill_active else "halted_by_kill_switch",
        "kill_switch_active": kill_active,
        "ledger_entries_count": len(ledger_entries),
        "ledger_integrity_valid": is_valid,
        "never_equate_intent_to_approval": True,
        "governance_provider": "A2Z SOC Gate/Prove Engine",
    }


@router.post("/verify", response_model=ActionVerificationResponse)
async def verify_agent_action(
    form_data: ActionVerificationRequest,
    user=Depends(get_verified_user),
):
    """
    Verifies an AI agent tool action against the zero-trust ActionBoundary.
    """
    action_id = f"act_{int(time.time() * 1000)}"
    timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Check emergency kill switch
    if check_kill_switch_active():
        entry = GLOBAL_ACTION_LEDGER.record_action(
            action_id=action_id,
            tool_name=form_data.tool_name,
            tool_tier=form_data.tool_tier,
            decision=GateDecision.REJECTED,
            payload=form_data.tool_input,
        )
        return ActionVerificationResponse(
            decision=GateDecision.REJECTED,
            allowed=False,
            reason="ActionGate emergency kill switch is actively engaged.",
            action_id=action_id,
            current_hash=entry["curr_hash"],
            timestamp=timestamp,
        )

    # 2. Simulation mode bypass
    if form_data.simulation_mode:
        entry = GLOBAL_ACTION_LEDGER.record_action(
            action_id=action_id,
            tool_name=form_data.tool_name,
            tool_tier=form_data.tool_tier,
            decision=GateDecision.SIMULATED,
            payload=form_data.tool_input,
        )
        return ActionVerificationResponse(
            decision=GateDecision.SIMULATED,
            allowed=True,
            reason="Simulation mode enabled: dry-run executed without state mutation.",
            action_id=action_id,
            current_hash=entry["curr_hash"],
            timestamp=timestamp,
        )

    # 3. Destructive / Admin tier requires explicit user confirmation
    if form_data.tool_tier in (ToolTier.DESTRUCTIVE, ToolTier.ADMIN):
        if not form_data.user_confirmed:
            entry = GLOBAL_ACTION_LEDGER.record_action(
                action_id=action_id,
                tool_name=form_data.tool_name,
                tool_tier=form_data.tool_tier,
                decision=GateDecision.CONFIRMATION_REQUIRED,
                payload=form_data.tool_input,
            )
            return ActionVerificationResponse(
                decision=GateDecision.CONFIRMATION_REQUIRED,
                allowed=False,
                reason=f"Action requires explicit user confirmation for tier '{form_data.tool_tier.value}'.",
                action_id=action_id,
                current_hash=entry["curr_hash"],
                timestamp=timestamp,
            )

    # 4. Standard validation passed
    entry = GLOBAL_ACTION_LEDGER.record_action(
        action_id=action_id,
        tool_name=form_data.tool_name,
        tool_tier=form_data.tool_tier,
        decision=GateDecision.ALLOWED,
        payload=form_data.tool_input,
    )

    return ActionVerificationResponse(
        decision=GateDecision.ALLOWED,
        allowed=True,
        reason="Action verified and authorized by ActionBoundary.",
        action_id=action_id,
        current_hash=entry["curr_hash"],
        timestamp=timestamp,
    )


@router.get("/ledger")
async def export_action_ledger(user=Depends(get_admin_user)):
    """
    Exports the cryptographic hash-chained Action Ledger for SOC 2 / ISO 42001 compliance audits.
    """
    entries = GLOBAL_ACTION_LEDGER.get_entries()
    is_valid = GLOBAL_ACTION_LEDGER.verify_integrity()

    return {
        "integrity_verified": is_valid,
        "total_actions": len(entries),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "ledger": entries,
    }
