# Release validation — 2026-09-25

Executed locally on macOS arm64 with Colima 0.10.3, Docker Engine 29.5.2 (Linux arm64), Python 3.12.13 and uv 0.12.19. Python 3.14.7 was also exercised during development, including 11 Docker integration tests with warnings treated as errors. Hosted GitHub Actions/CodeQL and native Linux amd64 execution have not yet run.

## Environment used

```bash
export PATH="/opt/homebrew/bin:$PATH"
export UV_CACHE_DIR=/private/tmp/vibesandbox-uv
export DOCKER_HOST=unix:///Users/sollutions/.colima/default/docker.sock
mkdir -p .sandbox-tmp
chmod 700 .sandbox-tmp
export TMPDIR="$PWD/.sandbox-tmp"
```

The socket and staging paths are local environment settings, not project defaults. No security policy was relaxed.

## Checks

| Command | Final result |
| --- | --- |
| `UV_PYTHON=/opt/homebrew/bin/python3.12 make setup` | Locked environment installed |
| `make lint` | Ruff lint and format passed |
| `make typecheck` | Strict mypy passed, 10 application files |
| `make test` | 42 unit/security regression tests passed |
| `make images` | Both digest-pinned runtime images built |
| `make test-integration` | 11 actual Docker integration tests passed |
| `make demo` | Seven safe scenarios passed; no demo containers remain |
| `make security` | Hash-pinned dependency export audited; no known vulnerabilities found |
| `make build` | Wheel and source distribution built |
| `.venv/bin/vibesandbox run examples/hello.py --json` | JSON parsed; completed, expected stdout, container removed |
| `DOCKER_HOST=unix:///private/tmp/vibesandbox-nonexistent.sock .venv/bin/pytest tests/integration -q` | 11 clean skips when Docker unavailable |
| `git diff --check` | No whitespace errors in tracked diff |
| `git status --short` | Only intended new repository files; generated artifacts ignored |

The wheel was installed into an isolated environment and executed against Docker:

```bash
uv run --isolated --no-project --python /opt/homebrew/bin/python3.12 \
  --with ./dist/vibesandbox-0.1.0-py3-none-any.whl \
  vibesandbox run examples/hello.py --json
```

It returned completed, the expected stdout and `container_removed: true`. The source distribution was inspected for unintended environments, IDE files, staging directories and bytecode; none were included. Workflow YAML was parsed locally; that is not a hosted CI run.

## Security scanning

The following scanner image was actually downloaded; its digest is recorded in CI:

```text
aquasec/trivy@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969
```

For each image (`vibesandbox-python:0.1.0`, `vibesandbox-node:0.1.0`), executed:

```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro \
  aquasec/trivy@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969 \
  image --scanners vuln --severity HIGH,CRITICAL --exit-code 1 IMAGE
```

Final result: no HIGH/CRITICAL findings in either runtime image. Initial Node findings were in package-manager dependencies; npm/Yarn and associated launchers were removed from the execution image, then it was rebuilt and rescanned. These tools are unnecessary for single-file execution. No vulnerability suppression was added. Python's Alpine 3.24 scan emitted a scanner EOL-list warning; this is not evidence of perpetual upstream support.

Repository scan:

```bash
docker run --rm -v "$PWD:/repo:ro" \
  aquasec/trivy@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969 \
  fs --scanners secret --skip-dirs /repo/.venv --skip-dirs /repo/.git --exit-code 1 /repo
```

Result: no detected secrets. Scanners are trusted maintenance tools, not submitted workloads. The Docker socket mount above belongs only to the scanner; VibeSandbox never gives it to executed code. Vulnerability results are point-in-time findings, not absence-of-vulnerability guarantees.

## Runtime evidence and limits

Successful Python/Node execution, expected stderr failure, timeout termination, network namespace containing only loopback plus ENETUNREACH, EROFS on root writes, capped process creation, memory exhaustion, bounded stdout/stderr, numeric non-root identity, no-new-privileges, empty effective capabilities, seccomp filter mode, read-only source and absence of Docker socket were exercised. Every integration execution checks the run-specific container is gone.

```bash
docker ps -a --filter label=io.sollutions.vibesandbox=true --format '{{.Names}}'
```

Result: no sandbox containers. Daemon outages and cleanup exceptions are covered with injected failures; power loss, kernel exploits and hostile multi-tenancy are not claimed as validated scenarios. Colima and the built images remain available for further local use. No HTTP API was added.
