"""Smoke tests: every example imports and builds its agents — no model call, no OpenAI key.

Importing a `main.py` executes its module body (agent/tool definitions + the
`openwright.instrument("openai-agents")` call), so these double as a build check for the
OpenWright integration and give the repo real, publishable coverage of the example code.
"""

from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(rel: str, name: str, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENWRIGHT_LEDGER", f"file://{tmp_path}/ledger")
    monkeypatch.setenv("OPENWRIGHT_SIGNING_KEY_FILE", str(tmp_path / "key.pem"))
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_customer_service_builds(tmp_path, monkeypatch):
    m = _load("examples/openai/customer_service/main.py", "cs_main", tmp_path, monkeypatch)
    assert m.triage_agent.name == "Triage Agent"
    assert any(t.name == "update_seat" for t in m.seat_booking_agent.tools)


def test_financial_research_builds(tmp_path, monkeypatch):
    m = _load("examples/openai/financial_research_agent/main.py", "fin_main", tmp_path, monkeypatch)
    assert m.planner_agent.name == "FinancialPlannerAgent"
    assert m.verifier_agent.name == "VerificationAgent"
