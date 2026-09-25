from pathlib import Path

import pytest
from pydantic import ValidationError

from vibesandbox.config import Policy, load_policy
from vibesandbox.runners.docker import container_options
from vibesandbox.runtimes import RUNTIMES, detect


@pytest.mark.parametrize(
    "field,value",
    [
        ("timeout", 0),
        ("timeout", float("nan")),
        ("memory_mb", 1),
        ("memory_mb", 2048),
        ("cpus", 0),
        ("pids", -1),
        ("output_bytes", 9999999),
        ("privileged", True),
        ("memory_mb", True),
    ],
)
def test_rejects_unsafe_policy(field, value):
    with pytest.raises(ValidationError):
        Policy.model_validate({field: value})


def test_default_policy_and_overrides():
    assert load_policy(Path("policies/default.yaml")) == Policy()
    assert load_policy(timeout=10.0).timeout == 10


@pytest.mark.parametrize("content", ["[]", "null", "privileged: true", "timeout: nope"])
def test_bad_policy(tmp_path, content):
    policy = tmp_path / "policy.yaml"
    policy.write_text(content)
    with pytest.raises(ValueError):
        load_policy(policy)


@pytest.mark.parametrize("runtime", RUNTIMES)
def test_security_configuration(runtime, tmp_path):
    p = Policy()
    options = container_options(tmp_path, runtime, p, "a" * 32)
    assert options["cap_drop"] == ["ALL"]
    assert options["network_disabled"] is True
    assert options["network_mode"] == "none"
    assert options["read_only"] is True
    assert options["security_opt"] == ["no-new-privileges:true"]
    assert options["user"] == "65532:65532"
    assert options["privileged"] is False
    assert options["pids_limit"] == p.pids
    assert options["mem_limit"] == options["memswap_limit"] == "128m"
    assert options["nano_cpus"] == 500_000_000
    mount = options["mounts"][0]
    assert mount["Source"] == str(tmp_path) and mount["Target"] == "/source"
    assert mount["ReadOnly"] is True and mount["Type"] == "bind"
    assert "volumes" not in options
    assert "noexec,nosuid,nodev" in options["tmpfs"]["/tmp"]
    assert options["log_config"]["Type"] == "none"
    assert options["command"] == runtime.command()
    assert options["tty"] is False
    assert "seccomp=unconfined" not in options["security_opt"]


@pytest.mark.parametrize("runtime", RUNTIMES)
def test_detection(runtime):
    assert detect(Path("untrusted;name" + runtime.extension)) == runtime


def test_unsupported():
    with pytest.raises(ValueError):
        detect(Path("file.sh"))
