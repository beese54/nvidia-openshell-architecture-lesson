# Live inspection of an OpenShell sandbox (2026-10-31)

This is a handoff note, so a new session doesn't redo the work. It records what was observed on this machine with `evidence/inspect.sh`, using a throwaway sandbox `eli5-8514` (created, then deleted).

**Setup:** OpenShell **0.1.2**, Docker compute driver, WSL 2 on Windows 11. The policy was the deny-all policy now saved as `evidence/policy_deny_all.yaml`, and the image was a private one with Python 3.12.

Evidence labels: **OBSERVED** = seen here. **DOCS** = docs.nvidia.com/openshell/latest. **INFERRED** = reasoning, not proven.

## Host side (OBSERVED)
- `/usr/bin/openshell-gateway` runs as a **native host process** (the login user, not root). It is not in a container.
- `openshell status`: gateway `https://127.0.0.1:17670`, "Authenticated (mTLS transport)", version 0.1.2.
- `openshell gateway info` lists these extensions:
  - `docker` (compute-driver)
  - `openshell-driver-db-credstore` (credential-driver)
  - `openshell/regex` (supervisor-middleware)
  - all with protocol 1.0
- OpenShell has its **own Docker engine**: systemd `docker-openshell.service`, `dockerd -H unix:///run/docker-openshell.sock --data-root /var/lib/docker-openshell`. It is separate from Docker Desktop.

## Per sandbox: two containers (OBSERVED via `docker inspect`)

| | Supervisor container | Workload container |
|---|---|---|
| Name | `openshell-default--<name>-<uuid>-supervisor` | `openshell-default--<name>-<uuid>` |
| Entrypoint | `/openshell-supervisor --backend-descriptor-file /.openshell/supervisor/runtime-descriptor.json --auth-bundle-file /.openshell/supervisor/auth.json --workdir /workspace --health-socket-path=/run/openshell/health.sock` | `/.openshell/runtime/openshell-sandbox --bootstrap /.openshell/channel/sandbox/bootstrap.json` |
| User | `65534:65534` (nobody) | `1000:1000` (sandbox) |
| NetworkMode | **host** | **none** |
| Capabilities | CapDrop=[ALL], Privileged=false | CapDrop=[ALL], Privileged=false |
| SecurityOpt | no-new-privileges:true | no-new-privileges:true |
| Mounts | channel volume → `/.openshell/channel` **ro**; supervisor volume → `/.openshell/supervisor` ro | the same channel volume → `/.openshell/channel` **rw** |

## Inside the workload (OBSERVED)
- `id`: uid=1000(sandbox) gid=1000(sandbox).
- `/proc/self/status`: CapEff 0, CapBnd 0, NoNewPrivs 1, **Seccomp 2** (filter mode), **Seccomp_filters 6**.
- Processes:
  - PID 1 `openshell-sandbox --bootstrap ...`
  - PID 80 `sleep infinity` (the user's command)
  - exec'd commands, all run as `sandbox`
- Network: `/proc/net/dev` shows **only `lo`**, and the routing table is **empty**.
- `/etc/resolv.conf`: `nameserver 127.0.0.53`.
- Env vars pointing at an OpenShell CA:
  - `SSL_CERT_FILE` and `GIT_SSL_CAINFO` → `/run/openshell-supervisor-ca/material/ca-bundle.crt`
  - `NODE_EXTRA_CA_CERTS` and `DENO_CERT` → `/run/openshell-supervisor-ca/material/ca.crt`
- Probes:
  - DNS `example.com` → **198.18.0.2**; a random made-up name → **198.18.0.3** (synthetic)
  - TCP connect 1.1.1.1:443 → **PermissionError Errno 13** (EACCES, not ENETUNREACH)
  - HTTPS urlopen → Errno 13
  - write `/workspace/x` → Errno 13 (the sandbox user owns `/workspace`, so this is Landlock)
  - `ls /home` → Errno 13 (not in the policy lists)

## Log lines (OBSERVED; `openshell logs <name> --source all`)
- gateway: `CreateSandbox request completed successfully`
- sandbox: `Starting sandbox supervision command=["sleep", "infinity"]`
- sandbox: `Fetching sandbox policy via gRPC endpoint=https://127.0.0.1:17670`
- gateway: `GetSandboxConfig served from spec`, then `GetSandboxProviderEnvironment`
- sandbox: `openshell_supervisor_network::opa Configured OPA runtime binary identity mode require_binary_identity=true`
- sandbox: `Isolation boundary attached`, then `Isolation boundary enforcement confirmed backend=openshell-sandbox`
- ocsf: `TLS termination enabled: ephemeral CA generated`
- ocsf: `Policy DNS connected to isolation boundary`
- ocsf: `NET:LISTEN 127.0.0.1:3128` (the proxy; whether that is host loopback or something else is **not yet confirmed**)
- WARN: `host.openshell.internal maps to a non-link-local IP; trusted-gateway SSRF exemption disabled ip=127.0.0.1`
- sandbox: `Isolation boundary agent started`; ocsf `SSH:LISTEN`; ocsf `NET:OPEN 127.0.0.1:17670` (supervisor dials out to the gateway)
- gateway: `supervisor session: accepted`
- ocsf: `CONFIG:LOADED Acknowledged initial policy revision as loaded [version:1] [hash:53ba4b...]`
- For each exec:
  - gateway: `ExecSandbox (relay): command started`, `relay stream: claimed pending relay, bridging`
  - sandbox: `ssh relay open (... target=unix:/run/openshell/ssh.sock)` and `SSH:OPEN ALLOWED`, then `ssh relay closed`
- `openshell sandbox get` annotations: `auth-epoch: 1`, `gateway-token-id`, `runtime-generation`. Conditions: `Ready: True (Supervisor session connected)`, `ConfigurationReady: True`.
- **Not seen:** an OCSF `DENIED` line for the 1.1.1.1 connect in the last 40 lines that were captured. Earlier private notes did record denial events, so re-check this with a bigger window. (Resolved 2026-11-11: see `tasks/doc_audit.md` row N5.)

## The exec path, as pieced together from the logs (OBSERVED + INFERRED)
1. The CLI sends `ExecSandbox` (gRPC, mTLS) to the gateway.
2. The supervisor dialed out to the gateway at startup. The gateway sends a relay request down that session.
3. The supervisor relays to `unix:/run/openshell/ssh.sock`, an SSH server run by `openshell-sandbox` in the workload. **Correction 2026-11-11:** the v0.1.2 source says the supervisor runs this SSH server; see `tasks/doc_audit.md` row E2.
4. The command runs as uid 1000, under Landlock and seccomp.

INFERRED: this SSH path explains two quirks seen when scripting the CLI. `exec` waits for stdin to close, and the image's ENV is dropped because each SSH session starts with a fresh environment.

## The connect() path (DOCS + OBSERVED result)
- **DOCS:** seccomp user notification pauses `connect()` and DNS calls. `openshell-sandbox` identifies the caller from trusted `/proc` data and forwards the request over the channel to the supervisor.
- The supervisor checks it against OPA (binary + host + port, then method/path if TLS is ended for HTTP). If allowed, it opens the real connection from the host side and relays the bytes, adding credentials only for approved endpoints.
- **OBSERVED:** the denied result reaches the agent as EACCES.

## Docs facts gathered (docs.nvidia.com/openshell/latest)
- **Policy sections:**
  - `filesystem_policy` (Landlock), `landlock`, `process` → **static**
  - `network_policies` and `network_middlewares` (proxy) → **dynamic**
- **Policy source precedence:** global → sandbox (`--policy`) → image → built-in restrictive default. An invalid image policy blocks startup; there is no fallback.
- **Network rules:**
  - Default deny. A deny beats an allow.
  - Binaries are matched by real path, with globs allowed. Children inherit the rule. The binary is hashed on first use, and a later change is denied.
  - L4 check, then L7 if `protocol` is set (rest / websocket / graphql / mcp / json-rpc / tcp).
  - `access: read-only` = GET/HEAD/OPTIONS. `tls: skip` relays without inspecting.
  - **`enforcement: audit` is the default**; `enforce` blocks.
  - Private, loopback, link-local and 169.254.169.254 addresses are blocked (anti-SSRF).
  - DNS placeholder addresses have TTL ≤ 30 s, and AAAA queries get an empty answer.
- **Credentials:** "Agents never see real credentials." A network rule alone does not authorize sending credentials; a provider binding does.
- **Phases:** Provisioning, Starting, Ready, Stopping/Stopped, Completed, Error, Deleting.
- **Generations:** each run gets fresh tokens and TLS certs. If the supervisor disconnects, the agent is frozen (fail closed).
- **The latest docs' architecture** describes a supervisor/workload split joined by a mutually authenticated HTTP/2 "Sandbox Protocol" (Unix socket for Docker, TCP for Kubernetes, vsock for VMs). Supported runtimes: Docker, Podman, Kubernetes, VM.

## Still to verify (plan step 2)
- Where `127.0.0.1:3128` (proxy) and `127.0.0.53` (DNS stub) actually listen.
- What files are in the channel volume.
- The CA files.
- Whether a denied connect produces an OCSF DENIED line.
- The providers, inference and gateways doc pages. WebFetch was unavailable at handoff; use the `web-fetch` agent.
