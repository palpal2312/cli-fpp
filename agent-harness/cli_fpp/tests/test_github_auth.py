"""Tests for GitHub auth layer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cli_fpp.core import github_auth


def test_get_token_from_env(monkeypatch):
    github_auth.clear_token_cache()
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    result = github_auth.get_token(use_cache=False)
    assert result.method == "env"
    assert result.token == "ghp_test"


def test_get_token_from_gh_cli(monkeypatch):
    github_auth.clear_token_cache()
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    with patch.object(github_auth, "get_token_from_env", return_value=None), patch.object(
        github_auth, "get_token_from_gh_cli", return_value="gho_test"
    ):
        result = github_auth.get_token(use_cache=False)
    assert result.method == "gh-cli"


def test_get_token_raises_without_auth(monkeypatch):
    github_auth.clear_token_cache()
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    with patch.object(github_auth, "get_token_from_gh_cli", return_value=None), patch.object(
        github_auth, "is_gh_installed", return_value=False
    ):
        with pytest.raises(github_auth.GitHubAuthError):
            github_auth.get_token(use_cache=False)


def test_version_at_least():
    assert github_auth.version_at_least((2, 20, 0), (2, 20, 0))
    assert github_auth.version_at_least((2, 21, 0), (2, 20, 0))
    assert not github_auth.version_at_least((2, 19, 0), (2, 20, 0))


def test_auth_status_not_installed():
    github_auth.clear_token_cache()
    with patch.object(github_auth, "is_gh_installed", return_value=False):
        st = github_auth.auth_status()
    assert st.installed is False
    assert st.authenticated is False
