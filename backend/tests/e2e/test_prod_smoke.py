"""
Production smoke test — exercises the live CF stack end-to-end.

Run after a deploy:
  UNSEARCH_BASE_URL=https://api.unsearch.dev \
  UNSEARCH_TEST_API_KEY=unsk_... \
  pytest tests/e2e/test_prod_smoke.py -v

Test coverage:
  - /health is up on api.unsearch.dev
  - / returns the marketing landing on unsearch.dev
  - /api/v1/auth/signup creates an ephemeral user
  - The issued JWT lets us list/create/revoke API keys
  - The created API key can hit /api/v1/search and /api/v1/neural/search
  - /api/v1/billing/usage returns the new user's quota
  - The Stripe webhook endpoint rejects unsigned requests with 400
"""
from __future__ import annotations

import os
import secrets
import time

import httpx
import pytest

BASE = os.environ.get("UNSEARCH_BASE_URL", "https://api.unsearch.dev").rstrip("/")
WEB = os.environ.get("UNSEARCH_WEB_URL", "https://unsearch.dev").rstrip("/")
SEEDED_KEY = os.environ.get("UNSEARCH_TEST_API_KEY")  # optional pre-provisioned key


# Skip this entire module in local testing or without a test API key
pytestmark = pytest.mark.skipif(
    os.environ.get("ENVIRONMENT") == "testing" or not os.environ.get("UNSEARCH_TEST_API_KEY"),
    reason="Production smoke tests skipped in local testing or when UNSEARCH_TEST_API_KEY is not set"
)


@pytest.fixture(scope="session")
def http() -> httpx.Client:
    with httpx.Client(timeout=30.0) as client:
        yield client


def test_api_health(http: httpx.Client) -> None:
    resp = http.get(f"{BASE}/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_web_landing(http: httpx.Client) -> None:
    resp = http.get(f"{WEB}/", follow_redirects=True)
    assert resp.status_code == 200
    assert "UnSearch" in resp.text


def test_signup_login_keys_search(http: httpx.Client) -> None:
    """End-to-end: create an account, mint a key, run a search, revoke."""
    email = f"smoke+{int(time.time())}-{secrets.token_hex(4)}@unsearch.dev"
    password = secrets.token_urlsafe(24)

    signup = http.post(
        f"{BASE}/api/v1/auth/signup",
        json={"email": email, "password": password, "full_name": "Smoke Test"},
    )
    assert signup.status_code == 201, signup.text
    token = signup.json()["token"]
    assert token

    me = http.get(f"{BASE}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["plan"] == "FREE"

    # Mint key
    key_resp = http.post(
        f"{BASE}/api/v1/auth/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "smoke-test"},
    )
    assert key_resp.status_code == 201, key_resp.text
    api_key = key_resp.json()["key"]
    key_id = key_resp.json().get("id")

    # Use key to search (FREE plan: 10/min — ample for one call)
    search = http.post(
        f"{BASE}/api/v1/search",
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        json={"query": "Cloudflare Workers in 2026", "max_results": 3, "use_cache": False},
    )
    # Search may 502 if container is cold; allow a single retry
    if search.status_code == 502:
        time.sleep(3)
        search = http.post(
            f"{BASE}/api/v1/search",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json={"query": "Cloudflare Workers in 2026", "max_results": 3, "use_cache": False},
        )
    assert search.status_code == 200, search.text

    # Neural search exercises the edge AI path
    neural = http.post(
        f"{BASE}/api/v1/neural/search",
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        json={"query": "Cloudflare Workers in 2026", "top_k": 3, "use_autoprompt": False},
    )
    assert neural.status_code == 200, neural.text

    # Usage rollover
    usage = http.get(
        f"{BASE}/api/v1/billing/usage",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert usage.status_code == 200

    # Revoke the key
    if key_id:
        revoke = http.delete(
            f"{BASE}/api/v1/auth/keys/{key_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert revoke.status_code == 200


def test_stripe_webhook_rejects_unsigned(http: httpx.Client) -> None:
    resp = http.post(
        f"{BASE}/api/v1/billing/webhook",
        content="{}",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


def test_unauth_search_returns_401(http: httpx.Client) -> None:
    resp = http.post(
        f"{BASE}/api/v1/search",
        json={"query": "no auth"},
    )
    assert resp.status_code == 401


@pytest.mark.skipif(not SEEDED_KEY, reason="no UNSEARCH_TEST_API_KEY")
def test_seeded_key_research_agent(http: httpx.Client) -> None:
    """Optional: exercise the multi-step research agent end-to-end."""
    start = http.post(
        f"{BASE}/api/v1/agent/research",
        headers={"X-API-Key": SEEDED_KEY, "Content-Type": "application/json"},
        json={"query": "Cloudflare Containers GA timeline", "depth": 2},
    )
    assert start.status_code == 202, start.text
    session_id = start.json()["session_id"]

    deadline = time.time() + 120
    while time.time() < deadline:
        poll = http.get(f"{BASE}/api/v1/agent/research/{session_id}")
        assert poll.status_code == 200
        if poll.json().get("status") in ("completed", "failed"):
            break
        time.sleep(2)
    assert poll.json()["status"] == "completed", poll.text
