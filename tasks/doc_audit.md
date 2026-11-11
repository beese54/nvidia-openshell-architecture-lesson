# Claims audit: OpenShell 0.1.2 (Docker driver, WSL 2)

Every fact shown in the diagram or the lesson must cite a row here. Built 2026-11-11 (plan step 1) and completed the same day with more source reading and two live runs (plan step 2).

## Evidence sources

| Tag | Meaning | Where |
|---|---|---|
| **OBS** | Observed on this machine | `evidence/live_inspection_2026-10-31.md` (sandbox `eli5-8514`, OpenShell 0.1.2) |
| **OBS-P** | Observed earlier in a private project that runs OpenShell 0.1.2 the same way. Its notes are not published, so these rows rest on the author's word | not in this repository |
| **OBS-A** | Observed 2026-11-11, deny path (`evidence/policy_deny_all.yaml`, sandbox `eli5-14017`) | `evidence/runs/run_a_deny_2026-11-11.txt` |
| **OBS-B** | Observed 2026-11-11, allow path (`evidence/policy_allow_example.yaml`, sandbox `eli5-16951`) | `evidence/runs/run_b_allow_2026-11-11.txt` |
| **SRC** | NVIDIA/OpenShell source at tag `v0.1.2` (commit `6648bd0c290e`), read 2026-11-11 | paths below are relative to that repo |
| **DOCS-L** | docs.nvidia.com/openshell/latest, noted on 2026-10-31. The page was not recorded and "latest" is now 0.1.8 | must be re-grounded in SRC before use |
| **INF** | Reasoning from other rows, not proven | |

## Status values

- **VERIFIED**: backed by OBS, OBS-P or SRC. If SRC only, the design is confirmed but the behaviour was not watched on this machine.
- **CORRECTED**: the plan or the handoff note said something different; this row replaces it.
- **RECHECK**: a DOCS-L claim that needs a v0.1.2 source or live check (step 2).
- **UNVERIFIED**: no evidence yet. Shown with an `[UNVERIFIED]` marker or cut.

## H. Host side

| ID | Claim | Evidence | Status |
|---|---|---|---|
| H1 | `openshell-gateway` is a native host process, not a container, run by the login user | OBS "Host side" | VERIFIED |
| H2 | The gateway listens on `https://127.0.0.1:17670`; the CLI authenticates with mTLS | OBS `openshell status` | VERIFIED |
| H3 | Gateway extensions: `docker` (compute driver), `openshell-driver-db-credstore` (credential driver), `openshell/regex` (supervisor middleware), protocol 1.0 | OBS `openshell gateway info` | VERIFIED |
| H4 | OpenShell uses its own Docker engine: `docker-openshell.service`, socket `/run/docker-openshell.sock`, data root `/var/lib/docker-openshell` | OBS; OBS-P | VERIFIED |
| H5 | The gateway is the control plane: API, durable state, policy and settings delivery, provider config, relay coordination | SRC `architecture/README.md:8-10,93` | VERIFIED |
| H6 | Drivers (compute, credentials, identity) sit behind gRPC-over-Unix-socket boundaries | SRC `architecture/README.md:69-72` (diagram) | VERIFIED (SRC only) |
| H7 | The supervisor dials **out** to the gateway and keeps a session open; the gateway never dials the sandbox | SRC `architecture/README.md:136-142`; OBS logs `NET:OPEN 127.0.0.1:17670`, `supervisor session: accepted` | VERIFIED |
| H8 | The gateway stores and delivers policy but makes no per-request network decision; that happens in the supervisor | SRC `architecture/security-policy.md:3-6` | VERIFIED (SRC only) |
| H9 | For a few seconds after WSL starts, the gateway refuses connections (`tcp connect error … Connection refused`), and `sandbox create` fails | Observed 2026-11-11: two inspection runs failed this way until the script waited for `openshell status` to say Connected | VERIFIED |

## C. The two containers per sandbox

| ID | Claim | Evidence | Status |
|---|---|---|---|
| C1 | Each sandbox is two containers: `…-supervisor` and the workload | OBS `docker inspect`; SRC `architecture/sandbox.md:580-583`, `architecture/compute-runtimes.md:302` | VERIFIED |
| C2 | Supervisor container: entrypoint `/openshell-supervisor`, user 65534:65534, `NetworkMode=host`, CapDrop ALL, `no-new-privileges` | OBS | VERIFIED |
| C3 | Workload container: entrypoint `openshell-sandbox --bootstrap …`, user 1000:1000, `NetworkMode=none`, CapDrop ALL, `no-new-privileges` | OBS | VERIFIED |
| C4 | Both mount the same channel volume at `/.openshell/channel`: read-only in the supervisor, read-write in the workload. The supervisor also has a private volume at `/.openshell/supervisor` | OBS mounts | VERIFIED |
| C5 | The supervisor's private volume holds its bootstrap and channel material; the workload receives only `openshell-sandbox`, the public CA material and its half of the channel | SRC `architecture/sandbox.md:580-583` | VERIFIED (SRC only) |
| C6 | `openshell-sandbox` reaches the workload from a digest-pinned volume; the supervisor runs from a companion image | SRC `architecture/compute-runtimes.md:387` | VERIFIED (SRC only) |
| C7 | Three trust levels: supervisor (holds gateway credentials, policy, proxy, SSH), sandbox (same non-root identity as the agent, installs seccomp listener and Landlock, owns child processes), agent child (zero capabilities, `no_new_privs`, Landlock, final syscall filter) | SRC `architecture/sandbox.md:9-15` | VERIFIED (SRC only) |
| C8 | `architecture/README.md:11-14` says the supervisor "runs inside every sandbox workload" and launches the agent. That is older wording: `sandbox.md:13` says it "never executes inside the agent workload", and C1-C3 show the split. The diagram follows `sandbox.md` and the observation | SRC both files; OBS | VERIFIED (inconsistency recorded) |
| C9 | The supervisor container has a read-only root filesystem and a minimal image with no shell tools | OBS-A `ReadonlyRootfs=true`; `docker exec … ls` → "executable file not found" | VERIFIED |

## W. Inside the workload

| ID | Claim | Evidence | Status |
|---|---|---|---|
| W1 | Processes run as uid 1000 (`sandbox`); PID 1 is `openshell-sandbox`; the user command and every exec are its descendants | OBS `id`, process list | VERIFIED |
| W2 | `CapEff 0`, `CapBnd 0`, `NoNewPrivs 1`, `Seccomp 2`, `Seccomp_filters 6` | OBS `/proc/self/status` | VERIFIED |
| W3 | Only the `lo` interface exists and the routing table is empty | OBS `/proc/net/dev`, `/proc/net/route` | VERIFIED |
| W4 | `/etc/resolv.conf` is `nameserver 127.0.0.53` | OBS; SRC `architecture/sandbox.md:277-279` | VERIFIED |
| W5 | TLS trust env vars (`SSL_CERT_FILE`, `CURL_CA_BUNDLE`, `REQUESTS_CA_BUNDLE`, `GIT_SSL_CAINFO`, `NODE_EXTRA_CA_CERTS`, `DENO_CERT`) point at `/run/openshell-supervisor-ca/material/` | OBS env; OBS-A env | VERIFIED |
| W6 | No proxy environment variable is set, and none is needed | SRC `architecture/sandbox.md:167,296-297,518-520`; OBS env grep printed only the CA variables; OBS-A and OBS-B `proxy env: none` | VERIFIED |
| W7 | Writing `/workspace/x` fails with Errno 13 although uid 1000 owns `/workspace`: Landlock alone blocks it | OBS; OBS-P | VERIFIED |
| W8 | `ls /home` fails with Errno 13: the path is in neither policy list | OBS; OBS-P | VERIFIED |
| W9 | The workdir must be writable by the sandbox user or startup fails ("image workspace validation failed") | OBS-P | VERIFIED |
| W10 | A mandatory Landlock self-protection baseline (ABI v3, Linux 6.2+) protects `/.openshell`, separately from the optional workload filesystem policy | SRC `architecture/sandbox.md:191-198,251`; OBS-A: `ls /.openshell` from inside the workload → Permission denied | VERIFIED (SRC only) |
| W11 | A directory can be protected twice: root-owned with no write bits, and listed read-only in the policy. Each layer was shown to block on its own | OBS-P | VERIFIED |

## X. The channel between the two halves

| ID | Claim | Evidence | Status |
|---|---|---|---|
| X1 | One mutually authenticated gRPC (HTTP/2) connection over a private Unix socket (Docker). `Exchange` streams carry lifecycle, exec, TCP and forwarding; one persistent `Mediate` stream carries DNS | SRC `architecture/sandbox.md:24-29,918-924` | VERIFIED (SRC only) |
| X2 | Each sandbox generation gets a fresh CA and separate server and client certificates | SRC `architecture/sandbox.md:71-73` | VERIFIED (SRC only) |
| X3 | The socket file names inside the channel volume. They cannot be listed from the workload (Landlock denies `ls /.openshell`) and the supervisor image has no `ls`. The only known path is `/.openshell/channel/sandbox/bootstrap.json` | OBS-A; C3 | UNVERIFIED (not shown; the diagram says only "a Unix socket in the channel volume", row X1) |
| X4 | General UDP is unsupported; only DNS over UDP is mediated | SRC `architecture/sandbox.md:28-29` | VERIFIED (SRC only) |

## E. The exec path

| ID | Claim | Evidence | Status |
|---|---|---|---|
| E1 | CLI sends `ExecSandbox` to the gateway; the gateway bridges a relay over the supervisor's existing session | OBS logs `ExecSandbox (relay): command started`, `relay stream: claimed pending relay, bridging` | VERIFIED |
| E2 | **The SSH server is run by the supervisor**, on `unix:/run/openshell/ssh.sock`. The plan and handoff note placed it in the workload under `openshell-sandbox`; that was wrong | SRC `architecture/sandbox.md:13,101,704-706`; OBS log `ssh relay open (… target=unix:/run/openshell/ssh.sock)` | CORRECTED |
| E3 | The command itself is started by `openshell-sandbox` in the workload, on request over an `Exchange` stream | SRC `architecture/sandbox.md:14,100-103`; OBS W1 | VERIFIED (hop not watched live) |
| E4 | `/run/openshell/` is inside the supervisor container (its health socket is `/run/openshell/health.sock`) | OBS C2 entrypoint flag | INF (step 2: list it) |
| E5 | Exec runs through a login shell (`bash -lc`) unless `--no-login-shell` selects `bash -c` | SRC `architecture/sandbox.md:720-726`; used at OBS-P | VERIFIED |
| E6 | `sandbox exec` waits for stdin to close | OBS-P | VERIFIED (cause is INF: an SSH session keeps stdin open) |
| E7 | `sandbox exec` does not carry the image's `ENV`; the project re-sends it with `--env` | OBS-P | VERIFIED (cause is INF) |
| E8 | A sandbox accepts at most 4,096 exec attempts per generation | SRC `architecture/sandbox.md:140-143` | VERIFIED (SRC only) |
| E9 | `upload` is a tar extract over the same SSH relay, running as the sandbox user, so Landlock and file permissions bound it | SRC `architecture/sandbox.md:727`; OBS-P | VERIFIED |
| E10 | Uploading from `/mnt/c` (DrvFS) delivered NUL bytes; the fix is to upload a Linux-side copy | OBS-P | VERIFIED (a WSL trap, not an OpenShell design fact) |

## N. The connect() path

| ID | Claim | Evidence | Status |
|---|---|---|---|
| N1 | `openshell-sandbox` installs one seccomp **user-notification** listener; every workload process inherits it. It intercepts socket setup, resolves the calling binary and holds `connect` until the supervisor decides | SRC `architecture/sandbox.md:167,230-236`; behaviour in OBS-A/OBS-B matches: no proxy variable, instant `EACCES`, `getpeername` returns the synthetic address | VERIFIED (mechanism from SRC; matching behaviour observed) |
| N2 | Enforcement uses no proxy env var, no nftables and no network-namespace setup | SRC `architecture/sandbox.md:167,296-297` | VERIFIED (SRC only) |
| N3 | Once allowed, data flows on ordinary kernel sockets; only setup goes through the notification path | SRC `architecture/sandbox.md:235-236` | VERIFIED (SRC only) |
| N4 | A denied connect returns `EACCES` (Errno 13) to the caller | OBS probe; OBS-P; SRC grep hits `crates/openshell-sandbox/src/main.rs:648-756`, `crates/openshell-isolation-interface/src/linux/seccomp_notify.rs:702` (context not yet read); OBS-A probes (`tcp 1.1.1.1:443`, `example.com:443`, `169.254.169.254:80`), each answered in under 10 ms | VERIFIED |
| N5 | Denials are logged as OCSF events: `NET:OPEN [MED] DENIED <binary> -> <host>:<port> [reason:transparent_tcp_policy_denied]` | OBS-P; OBS-A, seven `DENIED` lines for this run | VERIFIED |
| N6 | The outer fence (`NetworkMode=none`) is independent: if the notification path misses a call, there is still no route out | SRC `architecture/sandbox.md:120,306-308`; OBS W3 | VERIFIED |
| N7 | A TCP open waits at most 30 s for a decision, then fails with `ETIMEDOUT`. An approval is tied to the socket that asked and cannot be transferred to another | SRC `architecture/sandbox.md:301-302`; same source lines, through `:304` | VERIFIED (SRC only) |
| N8 | The policy proxy checks destination, binary identity, TLS/L7 rules and SSRF, using OPA | SRC `architecture/sandbox.md:169`, `architecture/README.md:100`; OBS log `openshell_supervisor_network::opa … require_binary_identity=true` | VERIFIED |
| N9 | Allowed connections are dialed by the supervisor from the host network, to addresses it resolved and pinned itself. The agent's socket only ever sees the synthetic address | OBS-B: `CONFIG:PUBLISHED Policy DNS mapped example.com resolved=<two real addresses> synthetic=198.18.0.2 ports=443`, then `NET:OPEN [INFO] ALLOWED /usr/local/bin/python3.12(0) -> example.com:443 [policy:example_read_only engine:opa]`; `getpeername=('198.18.0.2', 443)` | VERIFIED |
| N10 | An explicit HTTP proxy (CONNECT and forward HTTP) exists as an adapter over the same pipeline, and the log shows `NET:LISTEN 127.0.0.1:3128`. In this setup nothing answers on that port: a connect from the workload's loopback and one from the host's loopback are both refused, and the host has no TCP listener on 3128 | SRC `architecture/sandbox.md:310-313`; OBS-A and OBS-B (`tcp 127.0.0.1:3128` → `ECONNREFUSED`; host `/dev/tcp` refused; host `ss -ltn`) | VERIFIED (unreachable here). What the logged listener is bound to is UNVERIFIED, so the diagram does not draw a proxy port |
| N11 | The log source named `sandbox` carries the supervisor's events (the OPA line comes from crate `openshell_supervisor_network`) | OBS log line | INF |
| N12 | A connect to an unused loopback port inside the sandbox returns `ECONNREFUSED`, not `EACCES`: sandbox-local loopback is left alone, so `EACCES` specifically means "policy said no" | OBS-A `tcp 127.0.0.1:9`; SRC `docs/how-it-works/policies/schema.mdx:142-143` | VERIFIED |
| N13 | An allowed hostname on a port the rule does not list is denied: `NET:OPEN DENIED … -> 198.18.0.2:80 [reason:transparent_tcp_mapping_denied]` | OBS-B | VERIFIED |
| N14 | The host's gateway port is not reachable from the workload (`127.0.0.1:17670` → `ECONNREFUSED`): the workload's loopback is its own | OBS-A, OBS-B | VERIFIED |
| N15 | Request-level (L7) enforcement works as written: with `protocol: rest`, `access: read-only`, `enforcement: enforce`, a GET returns 200 (`HTTP:GET [INFO] ALLOWED … engine:l7`) and a POST returns HTTP 403 with a JSON body `{"error":"policy_denied","layer":"l7",…}` (`HTTP:POST [MED] DENIED`) | OBS-B | VERIFIED |

## D. DNS

| ID | Claim | Evidence | Status |
|---|---|---|---|
| D1 | A sandbox-local resolver answers at `127.0.0.53:53` and forwards queries to the supervisor, which applies hostname policy | SRC `architecture/sandbox.md:277-280`; OBS W4; OBS-A: `/proc/net/tcp` and `/proc/net/udp` show `127.0.0.53:53` listening inside the workload, owned by uid 1000 | VERIFIED |
| D2 | Answers are synthetic `198.18.0.0/15` addresses, even for made-up names | OBS probe (198.18.0.2, 198.18.0.3); OBS-P | VERIFIED |
| D3 | For a name the policy allows, the synthetic address is tied to the name, ports, policy generation and the validated real addresses; the connection is later dialed only to those pinned addresses | SRC `architecture/sandbox.md:333-339` | VERIFIED (SRC only) |
| D4 | A name absent from policy gets only an "observation" address, and the lookup is logged `NET:REFUSE [MED] DENIED <name> [reason:policy_dns_ineligible]` | SRC `architecture/sandbox.md:335-337`; OBS-P; OBS-A `CONFIG:OBSERVATION Policy DNS staged unapproved name example.com synthetic=198.18.0.2 for TCP policy review` | VERIFIED |
| D5 | A name the policy does not allow is never sent to a real resolver: the trusted resolver is called only after the name passes policy | SRC `crates/openshell-supervisor-network/src/policy_dns/mod.rs:161-162` | VERIFIED (SRC only) |
| D6 | Placeholder addresses have a TTL of at most 30 s, so clients must re-resolve; AAAA queries get an empty answer | SRC `docs/how-it-works/policies/network-rules.mdx:602-609`; OBS-A `dns AAAA example.com: gaierror … No address` | VERIFIED (TTL from SRC only) |
| D7 | For an allowed name the supervisor resolves the real addresses itself and pins them to the synthetic address and the allowed ports | OBS-B `CONFIG:PUBLISHED Policy DNS mapped example.com resolved=… synthetic=198.18.0.2 ports=443` | VERIFIED |

## P. Policy

| ID | Claim | Evidence | Status |
|---|---|---|---|
| P1 | The deny-all policy used in run A: `/workspace` and system paths read-only, `/tmp` and `/dev/null` read-write, `include_workdir: false`, `landlock.compatibility: best_effort`, no `network_policies` | `evidence/policy_deny_all.yaml`; OBS-A (the policy is echoed by `openshell sandbox get`) | VERIFIED |
| P2 | No `network_policies` entry means all outbound traffic is denied | OBS-A probes: HTTPS, raw TCP and the metadata address all fail with `EACCES` | VERIFIED |
| P3 | Static fields (filesystem, Landlock, process) are fixed after first activation; network policy can change live | SRC `architecture/README.md:152-156`, `architecture/sandbox.md:811-814,892-894`; SRC `docs/how-it-works/policies/schema.mdx:26-37` | VERIFIED (SRC only) |
| P4 | The supervisor fetches policy from the gateway, builds the OPA engine, then acknowledges the revision as `LOADED` | SRC `architecture/sandbox.md:846-850`; OBS logs `Fetching sandbox policy via gRPC`, `CONFIG:LOADED … [version:1]` | VERIFIED |
| P5 | Filesystem and Landlock rules are applied by `openshell-sandbox` inside the workload; network rules are evaluated by the supervisor | SRC `architecture/sandbox.md:13-14,165-169` | VERIFIED (SRC only) |
| P6 | Policy precedence: global policy, then the sandbox's saved policy (`--policy`), then a policy in the image, then the restrictive default. A global policy replaces the sandbox's own. An invalid image policy blocks startup | SRC `docs/how-it-works/policies/overview.mdx:59-67,85`, `architecture/sandbox.md:773-775` | VERIFIED (SRC only) |
| P7 | Network rule evaluation: no match means deny; an explicit deny beats any allow; a binary is matched by its real path, and processes it starts inherit the rule; the executable is hashed on first use and a changed file is denied later; the connection check comes first, then per-request checks if `protocol` is set | SRC `architecture/security-policy.md:60-71`, `docs/how-it-works/policies/network-rules.mdx:61-77,79-90,144` | VERIFIED (SRC only; binary mismatch not tested live) |
| P8 | Policy can never authorize loopback, link-local or unspecified destinations, including the metadata address `169.254.169.254`. Private addresses are reachable only through an exact hostname that resolves to them, or `allowed_ips` | SRC `docs/how-it-works/policies/schema.mdx:135-149`; OBS-A and OBS-B: `169.254.169.254:80` → `EACCES` | VERIFIED. Corrects an earlier note, which said private addresses are always blocked |
| P9 | A denied L4 connect becomes a pending rule proposal at the gateway (`openshell rule get --status pending`), flushed every 10 s | SRC `architecture/sandbox.md:755-759`; OBS-A: `openshell rule get --status pending` showed no proposal a few seconds after seven denials | VERIFIED (SRC only; not observed here) |
| P10 | A policy is at most 4 MiB and is rejected if it has unknown fields or duplicate keys | SRC `docs/how-it-works/policies/schema.mdx:11-13` | VERIFIED (SRC only) |
| P11 | Filesystem paths that are not listed are inaccessible. `include_workdir` defaults to `false` when `filesystem_policy` is present | SRC `docs/how-it-works/policies/schema.mdx:47-49` | VERIFIED (SRC only) |
| P12 | Access presets: `read-only` = GET, HEAD, OPTIONS; `read-write` adds POST, PUT, PATCH; `full` = everything | SRC `docs/how-it-works/policies/schema.mdx:233-237`; OBS-B for `read-only` | VERIFIED |
| P13 | `process.run_as_user` and `run_as_group` set the workload's identity; root is rejected. Without them Docker uses the image's `USER` | SRC `docs/how-it-works/policies/schema.mdx:82-94` | VERIFIED (SRC only) |

## T. TLS and credentials

| ID | Claim | Evidence | Status |
|---|---|---|---|
| T1 | The supervisor generates an ephemeral CA for TLS termination | OBS log `TLS termination enabled: ephemeral CA generated` | VERIFIED |
| T2 | The workload gets only public CA material; the private key stays with the supervisor | SRC `architecture/sandbox.md:580-588`; OBS W5; OBS-B: `ca.crt` and `ca-bundle.crt` exist, read-only, on a tmpfs; there is no `ca.key`; the directory itself cannot be listed | VERIFIED |
| T3 | For an allowed HTTPS endpoint, the agent sees a certificate issued by `OpenShell Sandbox CA` for the real hostname, because the supervisor terminates TLS to inspect requests | OBS-B `tls example.com: … issuer=CN OpenShell Sandbox CA, O OpenShell; subject=CN example.com`; SRC `architecture/security-policy.md:97-100` | VERIFIED |
| T4 | Provider credentials live at the gateway. The agent sees placeholders; the proxy swaps in the real value per request, only after policy admits it and only for the provider's own endpoints | SRC `architecture/sandbox.md:352-356,621-634` | VERIFIED (SRC only). **Not used in this setup** (`--no-auto-providers`, `openshell_env.py:120`) |
| T5 | Middleware (`openshell/regex` here) runs after L7 policy and before credential injection, and cannot see injected credentials | SRC `architecture/sandbox.md:402-403,466-468` | VERIFIED (SRC only) |
| T6 | Even without `protocol`, OpenShell terminates TLS unless the endpoint sets `tls: skip`; with `tls: skip` it cannot inspect the traffic | SRC `docs/how-it-works/policies/network-rules.mdx:103-108`, `schema.mdx:156` | VERIFIED (SRC only) |

## L. Lifecycle and trust

| ID | Claim | Evidence | Status |
|---|---|---|---|
| L1 | Startup order: driver installs the outer fence and starts `openshell-sandbox` → sandbox listens, runs nothing untrusted → supervisor loads policy and attaches → sandbox installs seccomp broker and Landlock, reports evidence → supervisor sends the launch permit → the main process starts | SRC `architecture/sandbox.md:83-103`; OBS log order (`Isolation boundary attached` → `enforcement confirmed` → `agent started`) | VERIFIED |
| L2 | Readiness is reported only after the boundary is confirmed and the gateway session is registered | SRC `architecture/sandbox.md:76-77`; OBS `Ready: True (Supervisor session connected)` | VERIFIED |
| L3 | Fail closed: the sandbox probes the channel every 5 s with a 10 s deadline. On loss it freezes the workload process tree; the supervisor has 30 s to reconnect and reconfirm, otherwise the workload is terminated (SIGTERM, then SIGKILL) | SRC `architecture/sandbox.md:36-45,895-900` | VERIFIED (SRC only) |
| L4 | A replacement supervisor cannot take over a running generation: the sandbox pins the first supervisor instance ID it accepts | SRC `architecture/sandbox.md:41-44` | VERIFIED (SRC only) |
| L5 | Annotations `auth-epoch`, `gateway-token-id`, `runtime-generation` appear on the sandbox | OBS `openshell sandbox get` | VERIFIED |
| L6 | Phases: Provisioning, Starting, Ready, Stopping/Stopped, Completed, Error, Deleting | DOCS-L; SRC mentions Provisioning, Ready, Stopped, Completed, Error; SRC `docs/how-it-works/sandboxes/overview.mdx:847-856` | VERIFIED (SRC only, apart from Ready) |
| L7 | A config-rejected sandbox stays `Provisioning` with `ConfigurationInvalid` for a 300 s repair window | SRC `architecture/sandbox.md:777-793` | VERIFIED (SRC only) |
| L8 | Sandbox names: at most 19 characters; reusing a just-deleted name is flaky | OBS-P | VERIFIED (observation only) |
| L9 | `--cpu` and `--memory` on create bound the workload; a 3 GiB allocation is killed under a 2 GiB limit | OBS-P; OBS-A: a sandbox created without these flags shows `Memory=0` (no limit) | VERIFIED |

## Z. Limits (what it does not protect you from)

| ID | Claim | Evidence | Status |
|---|---|---|---|
| Z1 | Workload and host share one kernel in the Docker driver; a kernel exploit bypasses every layer above it | C1-C3 (containers, not VMs); SRC lists a VM driver as the alternative `architecture/compute-runtimes.md:298-302` | INF from VERIFIED rows |
| Z2 | `landlock.compatibility: best_effort` (the default, and the project's setting): if the filesystem rules cannot be applied, the sandbox **runs without them** and logs a high-severity finding. `hard_requirement` refuses to start instead. Neither relaxes the mandatory baseline | SRC `docs/how-it-works/policies/schema.mdx:65-80`, `docs/about/support-matrix.mdx:166` | VERIFIED (SRC only) |
| Z3 | Request rules on an inspected endpoint default to `enforcement: audit`: violations are logged and allowed. Only `enforce` blocks | SRC `docs/how-it-works/policies/schema.mdx:157`, `network-rules.mdx:118-122` | VERIFIED (SRC only; `enforce` observed in N15) |
| Z4 | Landlock denials produce no OpenShell log line; only network denials are in OCSF | OBS-A and OBS-B: the refused writes to `/workspace/x` left no line in the sandbox log; OBS-P | VERIFIED (observation) |
| Z5 | DNS query text is visible to OpenShell even when denied | OBS-P | VERIFIED (follows from D1) |
| Z6 | The supervisor container uses the host network, but it exposes no TCP listener on the host: `ss -ltn` shows only the gateway's 17670 and the system resolver | OBS-A and OBS-B host listeners | VERIFIED |
| Z7 | A `protocol: tcp` or uninspected endpoint is a routing constraint, not an application boundary: OpenShell does not check which service behind a shared front door the payload addresses. A wildcard host also lets the agent leak data through DNS labels | SRC `architecture/security-policy.md:118-123`, `docs/how-it-works/policies/network-rules.mdx:595-599` | VERIFIED (SRC only) |

## Counts (2026-11-11, after step 2)

- 100 claim rows (J rows excluded), counted by script on the first word of each Status cell: 95 VERIFIED (34 of them from source only), 1 CORRECTED, 3 INF, 0 RECHECK, 1 UNVERIFIED.
- Not shown as fact anywhere: the UNVERIFIED row (X3) and what the logged proxy listener is bound to (N10).
- Never tested live, so shown with the SOURCE badge only: the fail-closed freeze (L3), binary hash mismatch (P7), provider credentials (T4), rule proposals (P9).
