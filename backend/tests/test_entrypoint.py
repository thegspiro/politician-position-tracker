"""Tests for the container entrypoint's privilege-drop handling.

The entrypoint is POSIX sh. These tests run it for real; the cases only cover
paths that exit before migrations or the server start, so no database or
network is touched.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ENTRYPOINT = Path(__file__).resolve().parents[1] / "docker-entrypoint.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("sh") is None, reason="requires a POSIX sh"
)


def _run(env_extra: dict[str, str]) -> subprocess.CompletedProcess:
    env = {"PATH": os.environ["PATH"], **env_extra}
    return subprocess.run(
        ["sh", str(ENTRYPOINT)], env=env, capture_output=True, text=True, timeout=30
    )


def test_entrypoint_is_valid_posix_sh():
    result = subprocess.run(["sh", "-n", str(ENTRYPOINT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(os.geteuid() != 0, reason="privilege drop only applies to root")
@pytest.mark.parametrize(
    "puid,pgid",
    [("abc", ""), ("99", "users"), ("99;id", ""), ("-1", "")],
)
def test_non_numeric_puid_or_pgid_is_rejected(puid, pgid):
    env = {"PUID": puid}
    if pgid:
        env["PGID"] = pgid
    result = _run(env)
    assert result.returncode == 1
    assert "must be numeric" in result.stderr
    assert "Running database migrations" not in result.stdout
