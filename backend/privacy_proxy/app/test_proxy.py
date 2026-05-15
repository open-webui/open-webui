#!/usr/bin/env python3
"""
Garnet Proxy — Manual Test Script
Run on cVM: docker exec garnet-privacy-proxy-1 python3 /service/app/test_proxy.py
"""

import urllib.request
import json

BASE_URL = "http://localhost:8080"
PASS = "✅"
FAIL = "❌"
results = []

SEP = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


def check(name, condition, got=""):
    status = PASS if condition else FAIL
    msg = f"{status} {name}"
    if not condition:
        msg += f" | got: {got}"
    print(msg)
    results.append((name, condition))


def post(path, payload, headers=None):
    data = json.dumps(payload).encode()
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=h)
    try:
        res = urllib.request.urlopen(req, timeout=10)
        return json.loads(res.read())
    except Exception as e:
        return {"error": str(e)}


def get(path):
    try:
        res = urllib.request.urlopen(f"{BASE_URL}{path}", timeout=10)
        return json.loads(res.read())
    except Exception as e:
        return {"error": str(e)}


print(SEP)
print("[TEST] Garnet Proxy — starting test suite")
print(SEP)

# ── T01 health ──────────────────────────────────────────
print("\n[T01] Health check")
res = get("/health")
check("health returns ok", res.get("status") == "ok", res)

# ── T02 logs.py import ──────────────────────────────────
print("\n[T02] logs.py import")
try:
    from app.logs import (
        log_health, log_garnet, log_in_user, log_out_user,
        log_file_pii, log_internal, log_privacy_off,
        log_to_llm, log_to_user, log_error, log_sep
    )
    check("logs.py imports cleanly", True)
except Exception as e:
    check("logs.py imports cleanly", False, str(e))

# ── T03 analyze — PERSON + ORG ──────────────────────────
print("\n[T03] /analyze — PERSON + ORGANIZATION")
res = post("/analyze", {"text": "Max Mustermann works at Enclaive GmbH"})
types = [e.get("type") for e in res.get("entities", [])]
check("PERSON detected", "PERSON" in types, types)
check("ORGANIZATION detected", "ORGANIZATION" in types, types)

# ── T04 analyze — EMAIL ──────────────────────────────────
print("\n[T04] /analyze — EMAIL_ADDRESS")
res = post("/analyze", {"text": "Contact me at max@enclaive.com"})
types = [e.get("type") for e in res.get("entities", [])]
check("EMAIL_ADDRESS detected", "EMAIL_ADDRESS" in types, types)

# ── T05 analyze — IBAN ───────────────────────────────────
print("\n[T05] /analyze — IBAN_CODE")
res = post("/analyze", {"text": "IBAN: DE89370400440532013000"})
types = [e.get("type") for e in res.get("entities", [])]
check("IBAN_CODE detected", "IBAN_CODE" in types, types)

# ── T06 analyze — PHONE ──────────────────────────────────
print("\n[T06] /analyze — PHONE_NUMBER")
res = post("/analyze", {"text": "Call me at +49 172 99887766"})
types = [e.get("type") for e in res.get("entities", [])]
check("PHONE_NUMBER detected", "PHONE_NUMBER" in types, types)

# ── T07 analyze — German text ────────────────────────────
print("\n[T07] /analyze — German NER")
res = post("/analyze", {"text": "Mein Name ist Thomas Müller von Siemens AG"})
types = [e.get("type") for e in res.get("entities", [])]
check("PERSON detected in German", "PERSON" in types, types)

# ── T08 analyze — entity filter ──────────────────────────
print("\n[T08] /analyze — entity filter (PERSON only)")
res = post(
    "/analyze",
    {"text": "Anna Schmidt, email: anna@test.com"},
    headers={"x-garnet-entities": "PERSON"}
)
types = [e.get("type") for e in res.get("entities", [])]
check("PERSON returned", "PERSON" in types, types)
check("EMAIL_ADDRESS filtered out", "EMAIL_ADDRESS" not in types, types)

# ── T09 analyze — no PII ─────────────────────────────────
print("\n[T09] /analyze — no PII in text")
res = post("/analyze", {"text": "What is the capital of France?"})
entities = res.get("entities", [])
check("no entities detected", len(entities) == 0, entities)

# ── T10 vault/scan ───────────────────────────────────────
print("\n[T10] /vault/scan — pseudonymizes file content")
res = post("/vault/scan", {
    "text": "Anna Schmidt, email: anna@enclaive.com, IBAN: DE89370400440532013000",
    "file_id": "test-file-001",
    "privacy_proxy": True
})
check("entity_count > 0", res.get("entity_count", 0) > 0, res.get("entity_count"))
check("pseudonymized_text contains token", "PERSON_" in res.get("pseudonymized_text", ""), res.get("pseudonymized_text", "")[:100])

# ── T11 vault/scan — privacy OFF ─────────────────────────
print("\n[T11] /vault/scan — privacy OFF returns raw text")
original = "Anna Schmidt works at Enclaive"
res = post("/vault/scan", {
    "text": original,
    "file_id": "test-file-002",
    "privacy_proxy": False
})
check("entity_count=0 when privacy OFF", res.get("entity_count") == 0, res.get("entity_count"))
check("text unchanged when privacy OFF", res.get("pseudonymized_text") == original, res.get("pseudonymized_text", "")[:80])

# ── SUMMARY ──────────────────────────────────────────────
print(f"\n{SEP}")
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
print(f"[RESULT] {passed}/{len(results)} passed — {failed} failed")
if failed:
    print("[FAILED TESTS]")
    for name, ok in results:
        if not ok:
            print(f"  {FAIL} {name}")
print(SEP)
