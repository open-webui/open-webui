import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from open_webui.clapnclaw.client import clapnclaw_client
from open_webui.clapnclaw.presets import PRESET_ACTIONS

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/clapnclaw", tags=["clapnclaw"])


# ── Integrations ────────────────────────────────────────────────────

@router.get("/integrations/status")
async def integrations_status():
    try:
        return await clapnclaw_client.get("/api/integrations/status")
    except Exception as e:
        log.error(f"integrations_status: {e}")
        raise HTTPException(502, "ClapNClaw API unreachable")


@router.get("/integrations/connect-url/{provider}")
async def integrations_connect_url(provider: str):
    try:
        return await clapnclaw_client.get(f"/api/integrations/connect-url/{provider}")
    except Exception as e:
        log.error(f"integrations_connect_url: {e}")
        raise HTTPException(502, "ClapNClaw API unreachable")


# ── Tokens ──────────────────────────────────────────────────────────

@router.get("/tokens/usage")
async def tokens_usage():
    try:
        return await clapnclaw_client.get("/api/tokens/usage")
    except Exception as e:
        log.error(f"tokens_usage: {e}")
        raise HTTPException(502, "ClapNClaw API unreachable")


# ── Billing ─────────────────────────────────────────────────────────

@router.get("/billing/plan")
async def billing_plan():
    try:
        return await clapnclaw_client.get("/api/billing/plan")
    except Exception as e:
        log.error(f"billing_plan: {e}")
        raise HTTPException(502, "ClapNClaw API unreachable")


class CheckoutRequest(BaseModel):
    plan: str


@router.post("/billing/checkout")
async def billing_checkout(body: CheckoutRequest):
    try:
        return await clapnclaw_client.post("/api/billing/checkout", body.model_dump())
    except Exception as e:
        log.error(f"billing_checkout: {e}")
        raise HTTPException(502, "ClapNClaw API unreachable")


class TokenAddonRequest(BaseModel):
    amount: int


@router.post("/billing/token-addon")
async def billing_token_addon(body: TokenAddonRequest):
    try:
        return await clapnclaw_client.post("/api/billing/token-addon", body.model_dump())
    except Exception as e:
        log.error(f"billing_token_addon: {e}")
        raise HTTPException(502, "ClapNClaw API unreachable")


# ── Team ────────────────────────────────────────────────────────────

@router.get("/team/members")
async def team_members():
    try:
        return await clapnclaw_client.get("/api/workspaces/me/members")
    except Exception as e:
        log.error(f"team_members: {e}")
        raise HTTPException(502, "ClapNClaw API unreachable")


class InviteRequest(BaseModel):
    email: str


@router.post("/team/invite")
async def team_invite(body: InviteRequest):
    try:
        return await clapnclaw_client.post("/api/workspaces/me/invite", body.model_dump())
    except Exception as e:
        log.error(f"team_invite: {e}")
        raise HTTPException(502, "ClapNClaw API unreachable")


# ── Onboarding ──────────────────────────────────────────────────────

class RunAgentRequest(BaseModel):
    providers: list[str]


@router.post("/onboarding/run-agent")
async def onboarding_run_agent(body: RunAgentRequest):
    try:
        return await clapnclaw_client.post("/api/onboarding/run-agent", body.model_dump())
    except Exception as e:
        log.error(f"onboarding_run_agent: {e}")
        raise HTTPException(502, "ClapNClaw API unreachable")


# ── Presets ─────────────────────────────────────────────────────────

@router.get("/presets")
async def get_presets():
    return PRESET_ACTIONS
