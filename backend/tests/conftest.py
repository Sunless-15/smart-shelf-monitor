"""Pytest configuration and global fixtures."""

import os
import pytest


@pytest.fixture(autouse=True)
def default_auth_env(monkeypatch):
    """Keep auth bypassed by default for legacy phase tests unless overridden by test module."""
    if "DISABLE_AUTH" not in os.environ:
        monkeypatch.setenv("DISABLE_AUTH", "true")
