import asyncio
import sys
from types import ModuleType
import unittest
from unittest.mock import MagicMock

# Mock FastAPI & framework dependencies if not installed
if "fastapi" not in sys.modules:
    fastapi_mod = ModuleType("fastapi")
    class APIRouter:
        def __init__(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return lambda f: f
        def post(self, *args, **kwargs): return lambda f: f
    fastapi_mod.APIRouter = APIRouter
    fastapi_mod.Depends = lambda x: x
    fastapi_mod.HTTPException = Exception
    fastapi_mod.Request = MagicMock
    fastapi_mod.status = MagicMock
    sys.modules["fastapi"] = fastapi_mod

if "pydantic" not in sys.modules:
    pydantic_mod = ModuleType("pydantic")
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    pydantic_mod.BaseModel = BaseModel
    pydantic_mod.Field = lambda *args, **kwargs: kwargs.get("default_factory", lambda: {})() if "default_factory" in kwargs else kwargs.get("default", None)
    sys.modules["pydantic"] = pydantic_mod

if "open_webui.utils.auth" not in sys.modules:
    auth_mod = ModuleType("open_webui.utils.auth")
    auth_mod.get_verified_user = lambda: MagicMock()
    auth_mod.get_admin_user = lambda: MagicMock()
    sys.modules["open_webui.utils.auth"] = auth_mod

if "typer" not in sys.modules:
    typer_mod = ModuleType("typer")
    typer_mod.Typer = MagicMock
    sys.modules["typer"] = typer_mod

for mod in ["uvicorn", "passlib", "passlib.context", "jose", "jwt"]:
    if mod not in sys.modules:
        sys.modules[mod] = ModuleType(mod)

from open_webui.routers.action_gate import (
    ActionGateLedger,
    ActionVerificationRequest,
    GateDecision,
    ToolTier,
    get_action_gate_status,
    verify_agent_action,
)


class TestActionGateRouter(unittest.TestCase):
    def setUp(self):
        self.ledger = ActionGateLedger()
        self.mock_user = MagicMock()
        self.mock_user.id = "usr_123"
        self.mock_user.role = "admin"

    def test_ledger_hash_chain_integrity(self):
        entry1 = self.ledger.record_action(
            action_id="act_1",
            tool_name="sql_query",
            tool_tier=ToolTier.READ_ONLY,
            decision=GateDecision.ALLOWED,
            payload={"query": "SELECT 1"},
        )
        entry2 = self.ledger.record_action(
            action_id="act_2",
            tool_name="shell_exec",
            tool_tier=ToolTier.MUTATING,
            decision=GateDecision.ALLOWED,
            payload={"cmd": "ls"},
        )

        self.assertEqual(entry1["index"], 0)
        self.assertEqual(entry2["index"], 1)
        self.assertEqual(entry2["prev_hash"], entry1["curr_hash"])
        self.assertTrue(self.ledger.verify_integrity())

    def test_verify_allowed_action(self):
        req = ActionVerificationRequest(
            tool_name="web_search",
            tool_input={"query": "A2Z SOC"},
            tool_tier=ToolTier.READ_ONLY,
        )
        res = asyncio.run(verify_agent_action(req, self.mock_user))
        self.assertEqual(res.decision, GateDecision.ALLOWED)
        self.assertTrue(res.allowed)

    def test_verify_destructive_action_requires_confirmation(self):
        req = ActionVerificationRequest(
            tool_name="delete_database",
            tool_input={"db": "prod"},
            tool_tier=ToolTier.DESTRUCTIVE,
            user_confirmed=False,
        )
        res = asyncio.run(verify_agent_action(req, self.mock_user))
        self.assertEqual(res.decision, GateDecision.CONFIRMATION_REQUIRED)
        self.assertFalse(res.allowed)

    def test_verify_destructive_action_with_confirmation(self):
        req = ActionVerificationRequest(
            tool_name="delete_database",
            tool_input={"db": "staging"},
            tool_tier=ToolTier.DESTRUCTIVE,
            user_confirmed=True,
        )
        res = asyncio.run(verify_agent_action(req, self.mock_user))
        self.assertEqual(res.decision, GateDecision.ALLOWED)
        self.assertTrue(res.allowed)

    def test_verify_simulation_mode(self):
        req = ActionVerificationRequest(
            tool_name="deploy_cluster",
            tool_input={"nodes": 10},
            tool_tier=ToolTier.ADMIN,
            simulation_mode=True,
        )
        res = asyncio.run(verify_agent_action(req, self.mock_user))
        self.assertEqual(res.decision, GateDecision.SIMULATED)
        self.assertTrue(res.allowed)

    def test_status_endpoint(self):
        res = asyncio.run(get_action_gate_status(self.mock_user))
        self.assertIn("status", res)
        self.assertTrue(res["never_equate_intent_to_approval"])


if __name__ == "__main__":
    unittest.main()
