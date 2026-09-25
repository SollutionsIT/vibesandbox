from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from docker.errors import APIError, NotFound

from vibesandbox.config import Policy
from vibesandbox.models import Result
from vibesandbox.runners.docker import Capture, DockerRunner
from vibesandbox.runtimes import RUNTIMES


@pytest.fixture
def backend(monkeypatch):
    client = Mock()
    client.api.base_url = "http+docker://localhost"
    client.info.return_value = dict(
        OSType="linux",
        MemoryLimit=True,
        SwapLimit=True,
        CpuCfsQuota=True,
        PidsLimit=True,
        SecurityOptions=["name=seccomp,profile=builtin"],
    )
    client.images.get.return_value.id = "sha256:verified"
    container = client.containers.create.return_value
    container.attrs = {"State": {"Running": False, "ExitCode": 0}}
    stream = Mock()
    stream.__iter__ = Mock(return_value=iter([(b"ok", b"err")]))
    container.attach.return_value = stream
    monkeypatch.setattr("vibesandbox.runners.docker.docker.from_env", lambda **kwargs: client)
    return client, container


def result():
    return Result(run_id="a" * 32, policy=Policy(timeout=0.1), started_at=datetime.now(UTC))


def test_capture_bounded():
    capture = Capture(4)
    capture.consume(iter([(b"123456", b"ab"), (b"flood", b"cdef")]))
    report = result()
    capture.apply(report)
    assert report.stdout == "1234" and report.stderr == "abcd"
    assert report.stdout_truncated and report.stderr_truncated


def test_success_and_cleanup(backend, tmp_path):
    client, container = backend
    report = result()
    DockerRunner().run(tmp_path, RUNTIMES[0], report)
    assert report.status == "completed"
    assert report.stdout == "ok"
    assert report.container_removed is True
    container.remove.assert_called_once_with(force=True, v=True)
    assert client.containers.create.call_args.kwargs["image"] == "sha256:verified"
    client.close.assert_called_once()


def test_start_failure_cleanup(backend, tmp_path):
    _, container = backend
    container.start.side_effect = APIError("failure")
    report = result()
    with pytest.raises(APIError):
        DockerRunner().run(tmp_path, RUNTIMES[0], report)
    assert report.container_removed is True


def test_lost_create_response_cleanup(backend, tmp_path):
    client, _ = backend
    client.containers.create.side_effect = APIError("lost response")
    report = result()
    with pytest.raises(APIError):
        DockerRunner().run(tmp_path, RUNTIMES[0], report)
    client.containers.get.assert_called_once_with("vibesandbox-" + report.run_id)
    client.containers.get.return_value.remove.assert_called_once()


def test_cleanup_failure_is_not_success(backend, tmp_path):
    _, container = backend
    container.remove.side_effect = APIError("unavailable")
    report = result()
    DockerRunner().run(tmp_path, RUNTIMES[0], report)
    assert report.status == "internal_error"
    assert report.container_removed is False
    assert report.run_id in report.cleanup_error
    assert container.remove.call_count == 3


def test_cleanup_not_found_is_success(backend, tmp_path):
    _, container = backend
    container.remove.side_effect = NotFound("already removed")
    report = result()
    DockerRunner().run(tmp_path, RUNTIMES[0], report)
    assert report.container_removed is True


def test_timeout_kills_and_removes(backend, tmp_path):
    _, container = backend
    container.attrs = {"State": {"Running": True, "ExitCode": 137}}
    report = result()
    DockerRunner().run(tmp_path, RUNTIMES[0], report)
    assert report.status == "timed_out" and report.timed_out
    container.kill.assert_called_once()
    assert report.container_removed is True


@pytest.mark.parametrize("url", ["https://remote:2376", "http+docker://ssh"])
def test_reject_remote_daemon(backend, tmp_path, url):
    client, _ = backend
    client.api.base_url = url
    with pytest.raises(ValueError, match="local"):
        DockerRunner().run(tmp_path, RUNTIMES[0], result())
    client.containers.create.assert_not_called()


def test_reject_missing_security_support(backend, tmp_path):
    client, _ = backend
    client.info.return_value["PidsLimit"] = False
    with pytest.raises(ValueError, match="controls"):
        DockerRunner().run(tmp_path, RUNTIMES[0], result())
    client.containers.create.assert_not_called()


def test_disconnected_stream_close_preserves_report(backend, tmp_path):
    _, container = backend
    stream = container.attach.return_value
    stream.close.side_effect = OSError("Socket is not connected")
    report = result()
    DockerRunner().run(tmp_path, RUNTIMES[0], report)
    assert report.status == "completed" and report.stdout == "ok"
    stream._response.close.assert_called_once()


def test_interrupt_still_removes_container(backend, tmp_path):
    _, container = backend
    container.start.side_effect = KeyboardInterrupt()
    report = result()
    with pytest.raises(KeyboardInterrupt):
        DockerRunner().run(tmp_path, RUNTIMES[0], report)
    assert report.container_removed is True


def test_seccomp_is_required(backend, tmp_path):
    client, _ = backend
    client.info.return_value["SecurityOptions"] = []
    with pytest.raises(ValueError, match="seccomp"):
        DockerRunner().run(tmp_path, RUNTIMES[0], result())
    client.containers.create.assert_not_called()
