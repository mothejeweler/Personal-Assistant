"""Smoke tests for Raj Assistant.

Run with:
  /Users/mothejeweler/Documents/.venv/bin/python smoke_tests.py
"""

from __future__ import annotations

import os
from fastapi.testclient import TestClient

import main


def run() -> int:
    client = TestClient(main.app)
    failed = 0

    # 1) Health check
    r = client.get("/")
    ok = r.status_code == 200 and r.json().get("status") == "online"
    print("[PASS] health endpoint" if ok else f"[FAIL] health endpoint: {r.status_code} {r.text}")
    failed += 0 if ok else 1

    # 2) Webhook verify invalid token should be blocked
    r = client.get("/webhook/facebook?hub.verify_token=wrong&hub.challenge=123")
    ok = r.status_code == 403
    print("[PASS] webhook rejects invalid token" if ok else f"[FAIL] webhook invalid token handling: {r.status_code}")
    failed += 0 if ok else 1

    # 3) Test message endpoint should enforce required field
    r = client.post("/test/message", json={})
    ok = r.status_code in (400, 500)
    print("[PASS] test endpoint validates message" if ok else f"[FAIL] message validation: {r.status_code} {r.text}")
    failed += 0 if ok else 1

    # 4) Admin status endpoint available (when no key configured)
    headers = {}
    if os.getenv("ADMIN_API_KEY"):
        headers["x-admin-key"] = os.getenv("ADMIN_API_KEY", "")
    r = client.get("/admin/personality/status", headers=headers)
    ok = r.status_code == 200
    print("[PASS] admin personality status" if ok else f"[FAIL] admin status: {r.status_code} {r.text}")
    failed += 0 if ok else 1

    print("\nSmoke test summary:", "PASS" if failed == 0 else f"FAIL ({failed} failures)")
    return failed


if __name__ == "__main__":
    raise SystemExit(run())
