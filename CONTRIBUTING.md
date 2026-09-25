# Contributing

Use Python 3.12+ and uv. Run `make setup`, then activate `.venv/bin/activate` if you want the `vibesandbox` command directly. A local Linux Docker daemon is required only for execution/integration tests. Read README's socket and macOS staging notes.

Before a PR, run `make lint typecheck test`, `make images test-integration demo`, `make security` and `make build`. Unit tests must not need Docker. Do not weaken isolation to make a failing test pass. Document any platform-specific limitation and distinguish mocks from actual execution.

Keep orchestration in the service/runner, argument construction in the runtime registry, and resource settings in the typed policy. New backends or runtime options must include security regression coverage. No shell-string execution, arbitrary host mounts, privilege switches or unbounded capture.

Use `uv lock --upgrade` for intentional dependency updates, review the diff, and rerun gates. Update pinned runtime image digests with current upstream manifests and image scans. Keep PRs focused; include behavior changes, threat implications and concrete validation results. Do not commit environments, caches, build outputs, secrets or submitted code beyond safe test fixtures.

Security reports follow [SECURITY.md](SECURITY.md).
