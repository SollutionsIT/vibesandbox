# Operations

## Policy bounds

Isolation cannot be disabled through CLI or YAML. Resource bounds:

| YAML key | Minimum | Maximum | Unit |
| --- | --- | --- | --- |
| timeout | 0.1 | 60 | seconds after start |
| memory_mb | 32 | 1024 | MiB |
| cpus | 0.1 | 2 | CPU quota |
| pids | 16 | 128 | tasks (includes threads) |
| tmpfs_mb | 1 | 64 | MiB |
| output_bytes | 256 | 1048576 | bytes per stream |
| source_bytes | 1 | 1048576 | source bytes |

The Node runtime also sets a 64 MiB V8 old-space ceiling. Total process memory remains subject to Docker's memory cap. UTF-8 replacement decoding can expand the serialized representation of invalid bytes; capture limits apply to raw bytes. CPU is a quota, not dedicated cores. Limits should be adjusted for legitimate workload needs within these bounds.

## Docker connection and staging

Start Docker before running. The SDK honors `DOCKER_HOST` and uses the default Unix socket otherwise; it does not read Docker CLI contexts. Set `DOCKER_HOST` from `docker context inspect` for Colima/Desktop installations using a non-default socket. Remote connections are deliberately rejected because source bind mounts refer to the local filesystem.

On Colima, create a private staging directory in your shared checkout: `mkdir -p .sandbox-tmp && chmod 700 .sandbox-tmp`, then `export TMPDIR="$PWD/.sandbox-tmp"`. On other VM-backed engines, select a private writable temporary location under an already shared host directory. Do not broadly share additional host directories to run a demo. Submitted paths must not contain symlinks, including macOS `/tmp` or `/var` aliases; pass their canonical `/private/...` paths instead. Temporary staging is internally created and trusted.

## Failure and recovery

- Missing image: `make images`; build failure stops Make with the Docker build error.
- Daemon unavailable: start Docker and check `DOCKER_HOST`; the report returns an internal error.
- Unsupported security controls: use a Linux daemon with cgroups and built-in seccomp; do not disable checks.
- Cleanup failure: the report includes the precise `docker rm -f` command. Inspect it and retry when Docker returns.
- After a host/control-plane crash, inspect `docker ps -a --filter label=io.sollutions.vibesandbox=true`. Remove only containers you know are abandoned; another CLI may be active.

Do not expose the Docker socket to untrusted users or publish an unauthenticated execution API. There is intentionally no v1 HTTP server: global admission control and authentication should precede it.

## Reproducibility and updates

`uv.lock` fixes the complete Python dependency resolution. Runtime Dockerfiles pin base-image manifest digests; `make images` builds with those bases. Update digests intentionally, review upstream changes and rerun both architecture-appropriate integration tests and image scans. Local image IDs are recorded in reports. The image build includes no application source and runs no package-manager install step.

GitHub CI uses immutable action SHAs resolved from actual release tags. Dependency auditing and image vulnerability databases change over time; a future finding should fail CI and trigger remediation, not be silently ignored. CodeQL's hosted workflow must run on GitHub to produce its actual analysis result.
