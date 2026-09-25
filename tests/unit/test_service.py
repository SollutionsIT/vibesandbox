import hashlib
import os
from unittest.mock import Mock

import pytest
from docker.errors import DockerException, ImageNotFound
from typer.testing import CliRunner

from vibesandbox.cli import app
from vibesandbox.config import Policy
from vibesandbox.models import Result
from vibesandbox.service import ExecutionService
from vibesandbox.source import read_source


@pytest.fixture
def source(tmp_path):
    # macOS /var and /tmp are symlinks; the strict API intentionally rejects them.
    path = tmp_path.resolve() / "input.py"
    path.write_text("print('ok')")
    return path


def test_snapshot_hash_and_serialization(source):
    snapshots = []

    def execute(directory, runtime, result):
        snapshots.append(directory)
        assert directory != source.parent
        assert (directory / "main.py").read_bytes() == source.read_bytes()
        assert (directory / "main.py").stat().st_mode & 0o222 == 0
        result.status = "completed"
        result.exit_code = 0

    result = ExecutionService(Mock(run=execute)).execute(source, Policy())
    assert result.status == "completed"
    assert result.source_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert len(result.run_id) == 32
    assert not snapshots[0].exists()
    assert Result.model_validate_json(result.model_dump_json()) == result
    assert result.finished_at >= result.started_at


@pytest.mark.parametrize(
    "exception,fragment",
    [
        (ImageNotFound("missing"), "image missing"),
        (DockerException("secret detail"), "Docker operation"),
        (RuntimeError("secret"), "internally"),
    ],
)
def test_error_mapping(source, exception, fragment):
    result = ExecutionService(Mock(run=Mock(side_effect=exception))).execute(source, Policy())
    assert result.status == "internal_error"
    assert fragment in result.error
    assert "secret" not in result.model_dump_json()


def test_invalid_source_never_runs(tmp_path):
    runner = Mock()
    assert ExecutionService(runner).execute(tmp_path / "bad.sh", Policy()).status == "policy_error"
    runner.run.assert_not_called()


def test_symlinks_traversal_size_and_fifo(source):
    link = source.parent / "link.py"
    link.symlink_to(source)
    directory = source.parent / "linked"
    directory.symlink_to(source.parent, target_is_directory=True)
    fifo = source.parent / "fifo.py"
    os.mkfifo(fifo)
    for path in (link, directory / "input.py", source.parent / ".." / "input.py", fifo):
        with pytest.raises((OSError, ValueError)):
            read_source(path, 100)
    with pytest.raises(ValueError, match="size"):
        read_source(source, 2)


@pytest.mark.parametrize(
    "args", [["--memory", "1g"], ["--timeout", "-1"], ["--policy", "/nonexistent"]]
)
def test_cli_invalid_policy_json(source, args):
    import json

    result = CliRunner().invoke(app, ["run", str(source), "--json", *args])
    assert result.exit_code == 2
    assert json.loads(result.stdout)["status"] == "policy_error"


def test_cli_success_json_and_safe_terminal(source, monkeypatch):
    import json
    from datetime import UTC, datetime

    report = Result(
        run_id="b" * 32,
        policy=Policy(),
        started_at=datetime.now(UTC),
        status="completed",
        stdout="\x1b[31m[link=evil]hello[/link]",
        container_removed=True,
    )
    monkeypatch.setattr("vibesandbox.cli.ExecutionService.execute", lambda *args: report)
    runner = CliRunner()
    output = runner.invoke(app, ["run", str(source), "--json", "--memory", "256m"])
    assert output.exit_code == 0
    assert json.loads(output.stdout)["stdout"] == report.stdout
    human = runner.invoke(app, ["run", str(source)])
    assert human.exit_code == 0
    assert "\x1b" not in human.stdout
    assert "[link=evil]hello[/link]" in human.stdout
