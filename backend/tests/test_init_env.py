"""Guard local credentials against accidental disclosure or replacement."""

import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

import pytest


@pytest.fixture
def project(tmp_path):
    root = Path(__file__).resolve().parents[2]
    (tmp_path / "infrastructure").mkdir()
    shutil.copy(root / "infrastructure/init_env.py", tmp_path / "infrastructure/init_env.py")
    shutil.copy(root / ".env.example", tmp_path / ".env.example")
    return tmp_path


def initialize(project):
    # Running elsewhere also checks that paths are relative to the script.
    return subprocess.run(
        [sys.executable, str(project / "infrastructure/init_env.py")],
        cwd=project.parent,
        capture_output=True,
        text=True,
        check=False,
    )


def test_generates_private_unique_credentials_without_logging_them(project):
    result = initialize(project)
    assert result.returncode == 0
    target = project / ".env"
    settings = dict(line.split("=", 1) for line in target.read_text().splitlines()
                    if line and not line.startswith("#"))
    password, token = settings["INFLUXDB_PASSWORD"], settings["INFLUXDB_TOKEN"]
    assert len(password) >= 32
    assert len(token) >= 48
    assert password != token
    assert password not in result.stdout + result.stderr
    assert token not in result.stdout + result.stderr
    if os.name == "posix":
        assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_preserves_existing_settings_byte_for_byte(project):
    target = project / ".env"
    contents = b"# local settings\r\nINFLUXDB_TOKEN=existing-token\r\n"
    target.write_bytes(contents)
    result = initialize(project)
    assert result.returncode == 0
    assert target.read_bytes() == contents


def test_refuses_new_credentials_for_an_existing_database(project):
    database = project / "data/influxdb/influxd.bolt"
    database.parent.mkdir(parents=True)
    database.write_bytes(b"database-state")
    result = initialize(project)
    assert result.returncode != 0
    assert "Restore its original .env" in result.stderr
    assert not (project / ".env").exists()
    assert database.read_bytes() == b"database-state"


@pytest.mark.skipif(os.name != "posix", reason="POSIX symbolic link behavior")
@pytest.mark.parametrize("existing_target", [True, False])
def test_does_not_follow_or_replace_environment_symlinks(project, existing_target):
    destination = project / "outside.env"
    if existing_target:
        destination.write_text("keep-this-content")
    (project / ".env").symlink_to(destination)
    result = initialize(project)
    assert result.returncode == 0
    assert (project / ".env").is_symlink()
    assert destination.exists() is existing_target
    if existing_target:
        assert destination.read_text() == "keep-this-content"
