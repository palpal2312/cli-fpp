"""Tests for controller doctor."""

from __future__ import annotations

from unittest.mock import patch

from cli_fpp.core import doctor


def test_run_doctor_ok_when_github_missing_but_other_ok():
    with patch.object(doctor, "_check_python", return_value={"ok": True, "version": "3.11"}), patch.object(
        doctor, "_check_cli_fpp", return_value={"ok": True, "version": "0.1.0"}
    ), patch.object(
        doctor,
        "_check_config",
        return_value={"ok": True, "target_count": 1, "contrib_enabled": True},
    ), patch.object(doctor, "_check_git", return_value={"ok": True, "version": "git 2"}), patch.object(
        doctor,
        "_check_github",
        return_value={"ok": False, "installed": False, "fix_hint": "winget install GitHub.cli"},
    ), patch.object(doctor, "_check_contrib", return_value={"ok": True, "pending": 0}):
        result = doctor.run_doctor()
    assert result["ok"] is False
    assert "github" in result["failed"]
    assert any("winget" in s for s in result["next_steps"])


def test_run_doctor_all_pass():
    with patch.object(doctor, "_check_python", return_value={"ok": True}), patch.object(
        doctor, "_check_cli_fpp", return_value={"ok": True}
    ), patch.object(doctor, "_check_config", return_value={"ok": True, "target_count": 1}), patch.object(
        doctor, "_check_git", return_value={"ok": True}
    ), patch.object(doctor, "_check_github", return_value={"ok": True}), patch.object(
        doctor, "_check_contrib", return_value={"ok": True}
    ):
        result = doctor.run_doctor(check_only=True)
    assert result["ok"] is True
    assert result["exit_code"] == 0
