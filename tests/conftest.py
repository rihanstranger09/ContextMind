"""Offline tests remain deterministic even when developer .env enables live billing."""
import pytest


@pytest.fixture(autouse=True)
def never_call_live_provider_implicitly(monkeypatch):
    # A test explicitly exercising the live agent can override this with its own fake client.
    monkeypatch.setenv('LLM_PROVIDER', 'disabled')
