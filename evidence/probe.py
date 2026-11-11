"""Read-only probes run INSIDE the sandbox workload by inspect.sh."""
import os, socket, ssl, subprocess, time, urllib.request, urllib.error


def show(label, fn):
    start = time.monotonic()
    try:
        out = fn()
    except Exception as e:  # report every failure, never stop
        out = f"{type(e).__name__}: {e}"
    print(f"{label}: {out}  [{time.monotonic() - start:.2f}s]")


def tcp(host, port):
    s = socket.socket()
    s.settimeout(8)
    try:
        s.connect((host, port))
        return f"connected, getpeername={s.getpeername()}"
    finally:
        s.close()


def tls_issuer(host):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=8) as raw:
        with ctx.wrap_socket(raw, server_hostname=host) as s:
            cert = s.getpeercert()
            return f"peer={s.getpeername()} issuer={cert.get('issuer')} subject={cert.get('subject')}"


def http(method, url):
    req = urllib.request.Request(url, method=method, data=b"x=1" if method == "POST" else None)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return f"HTTP {r.status}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code} body={e.read(200)!r}"


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    return "\n" + (r.stdout + r.stderr).rstrip()


print("proxy env:", {k: v for k, v in os.environ.items() if "proxy" in k.lower()} or "none")
show("dns example.com", lambda: socket.gethostbyname("example.com"))
show("dns made-up name", lambda: socket.gethostbyname("zzq-random-123.example.org"))
show("dns AAAA example.com", lambda: socket.getaddrinfo("example.com", 443, socket.AF_INET6))
show("tcp 1.1.1.1:443", lambda: tcp("1.1.1.1", 443))
show("tcp example.com:443", lambda: tcp("example.com", 443))
show("tcp example.com:80", lambda: tcp("example.com", 80))
show("tcp 127.0.0.1:9 (unused loopback port)", lambda: tcp("127.0.0.1", 9))
show("tcp 127.0.0.1:3128 (proxy port?)", lambda: tcp("127.0.0.1", 3128))
show("tcp 127.0.0.1:17670 (gateway port)", lambda: tcp("127.0.0.1", 17670))
show("tcp 169.254.169.254:80 (metadata)", lambda: tcp("169.254.169.254", 80))
show("tls example.com", lambda: tls_issuer("example.com"))
show("GET https://example.com/", lambda: http("GET", "https://example.com/"))
show("POST https://example.com/", lambda: http("POST", "https://example.com/"))
show("CA file ca.crt", lambda: {k: v for k, v in ssl._ssl._test_decode_cert("/run/openshell-supervisor-ca/material/ca.crt").items() if k in ("issuer", "subject", "notAfter")})
show("CA dir files by name", lambda: sh("ls -la /run/openshell-supervisor-ca/material/ca.crt /run/openshell-supervisor-ca/material/ca-bundle.crt /run/openshell-supervisor-ca/material/ca.key 2>&1"))
show("another binary (curl) to example.com", lambda: sh("readlink -f $(command -v curl wget | head -1); curl -sS -o /dev/null -w 'curl http_code=%{http_code}' --max-time 8 https://example.com/ 2>&1 || wget -q -T 8 -O /dev/null https://example.com/ 2>&1; echo \" rc=$?\""))
show("write /workspace/x", lambda: open("/workspace/x", "w") and "ok")
show("write /tmp/x", lambda: open("/tmp/x", "w") and "ok")
show("ls /home", lambda: os.listdir("/home"))
show("ls /.openshell", lambda: sh("ls -la /.openshell /.openshell/* 2>&1 | head -40"))
show("ls CA dir", lambda: sh("ls -la /run/openshell-supervisor-ca /run/openshell-supervisor-ca/* 2>&1 | head -20"))
show("ls /run", lambda: sh("ls -la /run /run/openshell 2>&1 | head -20"))
show("listening sockets (/proc/net/tcp, state 0A)", lambda: sh("awk 'NR==1 || $4==\"0A\"' /proc/net/tcp; echo udp:; cat /proc/net/udp"))
show("mounts with openshell", lambda: sh("grep -i -E 'openshell|workspace' /proc/self/mountinfo | cut -c1-200"))
