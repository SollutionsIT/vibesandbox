# Threat model

## Scope and assets

VibeSandbox runs one untrusted Python or JavaScript file using a trusted local Linux Docker daemon. Protect assets on the host: filesystem, credentials, network access, Docker daemon and other workloads. Threat actors include buggy AI-generated code, accidentally unsafe generated code and deliberately hostile submissions. The CLI caller, policy files, installed package, image builder and Docker daemon are trusted operators/components. This is not a service for mutually distrustful tenants.

## Trust boundaries

1. An untrusted filename and file contents enter the trusted control plane. Component-by-component `openat`/`O_NOFOLLOW` traversal rejects symlinks; bounded reads reject special files and oversized input. Concurrent modification by another trusted host process can change bytes during the read; the hash always describes the resulting executed snapshot.
2. The control plane copies only those bytes into a private temporary parent, with a read-only file inside a mounted source directory. The original path is never passed to Docker. The daemon has access to the host and must be trusted.
3. A fresh non-root container executes an argument-array command. No host namespaces, devices, credentials, ports, privileged mode or Docker socket are requested. Images are resolved to local immutable IDs before creation.
4. Untrusted stdout/stderr cross back through bounded in-memory capture. Docker logging is disabled. JSON is data; terminal presentation escapes non-printable control characters. Consumers must not execute or render returned text as trusted markup.

## Controls

- Network namespace with `none`; loopback within the sandbox remains available.
- Read-only root and source; size-limited scratch tmpfs with noexec/nosuid/nodev. Docker's normal writable pseudo-filesystems and a bounded `/dev/shm` remain present. `noexec` does not prevent an interpreter reading a script.
- Numeric non-root user, all capabilities dropped, no-new-privileges and Docker default seccomp. Missing seccomp or resource-control support is rejected before container creation.
- Memory and swap cap, CPU quota, PID cap, file-descriptor limit, core dumps disabled, source/output limits and execution deadline.
- A unique random container name, finally-style force removal, retries, and explicit cleanup failure. Lost create responses trigger lookup/removal by the already chosen name.

## Residual risks and operational limits

Docker shares the host kernel. Docker is not considered equivalent to a hardened VM/microVM security boundary for fully hostile multi-tenant production execution. Kernel/runtime vulnerabilities, side channels, malicious images, daemon compromise and Docker socket access can invalidate controls. On Desktop/Colima the Linux VM adds a host boundary, but its shared folders and daemon privileges still matter.

Per-run limits do not provide global admission control: many concurrent CLI invocations can exhaust the machine. Docker API calls and cleanup add time beyond the execution deadline; daemon stalls can delay termination. Streaming discards excess output but still spends bounded-per-chunk CPU processing it until timeout. Runtime base images include system utilities; “minimal” does not mean distroless or shell-free.

SIGKILL, host crash or permanent daemon loss can leave containers behind. Reports expose cleanup failures with the exact container name. Operators must inspect owned containers after such events. The temporary source is deleted after the runner returns; a running container after failed cleanup may retain access to its already-mounted snapshot. The package does not store reports or submitted source permanently.

## Non-goals and future boundaries

No malware detection, escape-proof execution, secret redaction of program output, dependency installation, arbitrary project mounting, public API, hostile multi-tenancy or Windows-host native execution. A local attacker with the same account or Docker permissions is outside the boundary.

Potential hardened backends: gVisor (userspace kernel), Kata Containers (VM-backed containers), Firecracker (microVMs). Each requires its own threat model and runtime regression suite; adding a name to configuration is not evidence of stronger isolation.

## References

- [Docker security](https://docs.docker.com/engine/security/)
- [Resource constraints](https://docs.docker.com/engine/containers/resource_constraints/)
- [Default seccomp profile](https://docs.docker.com/engine/security/seccomp/)
