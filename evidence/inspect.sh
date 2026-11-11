#!/usr/bin/env bash
# Read-only look inside a throwaway OpenShell sandbox, to ground the diagram.
# Run from WSL in a LOGIN shell (a plain `bash` fails to create the sandbox):
#   wsl -e env IMG=my-image:tag POLICY=/path/to/policy.yaml bash -l /path/to/this/repo/evidence/inspect.sh
# POLICY is an OpenShell policy file and IMG an image with python3. Run A used
# evidence/policy_deny_all.yaml (deny everything); run B used
# evidence/policy_allow_example.yaml (allow one host).
# The sandbox is deleted at the end.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
export DOCKER_HOST=unix:///run/docker-openshell.sock
D=/opt/docker-openshell/bin/docker
POLICY=${POLICY:?set POLICY to the path of an OpenShell policy yaml}
IMG=${IMG:?set IMG to an image in OpenShell's Docker engine that has python3}
NAME=eli5-$RANDOM
# After WSL starts, the gateway needs a few seconds before it accepts connections.
for i in $(seq 1 60); do openshell status 2>/dev/null | grep -q "Status: Connected" && break; sleep 1; done
echo "== openshell $(openshell --version)  image $IMG  name $NAME  policy $(basename "$POLICY")"
openshell sandbox create --name $NAME --from $IMG --policy $POLICY --detach --no-auto-providers -- sleep infinity 2>&1 | tail -3
for i in $(seq 1 120); do openshell sandbox get $NAME --color never 2>/dev/null | grep -q 'Phase: *Ready' && break; sleep 0.5; done
openshell sandbox get $NAME --color never
echo "== containers"; $D ps --format '{{.Names}} | {{.Image}} | {{.Command}}'
for c in $($D ps --format '{{.Names}}' | grep "$NAME"); do
  echo "== inspect $c"
  $D inspect $c --format 'NetworkMode={{.HostConfig.NetworkMode}} User={{.Config.User}} Privileged={{.HostConfig.Privileged}} CapDrop={{.HostConfig.CapDrop}} SecOpt={{.HostConfig.SecurityOpt}} PidMode={{.HostConfig.PidMode}} ReadonlyRootfs={{.HostConfig.ReadonlyRootfs}} Memory={{.HostConfig.Memory}} Entrypoint={{.Config.Entrypoint}}'
  $D inspect $c --format '{{range .Mounts}}MOUNT {{.Type}} {{.Name}} -> {{.Destination}} rw={{.RW}}{{"\n"}}{{end}}'
done
SUP=$($D ps --format '{{.Names}}' | grep "$NAME" | grep supervisor | head -1)
echo "== supervisor container processes (docker top)"; $D top "$SUP" 2>&1 | cut -c1-200
echo "== supervisor container: ls /run/openshell and channel (may fail: minimal image)"
$D exec "$SUP" ls -la /run/openshell /.openshell/channel /.openshell/supervisor 2>&1 | head -30
echo "== host listeners (ss -ltnp/-lunp, filtered)"
ss -ltnpH 2>/dev/null | grep -E ':(3128|17670|53|22)\b|openshell' | cut -c1-200
ss -lunpH 2>/dev/null | grep -E ':53\b|openshell' | cut -c1-200
echo "== host: can a host process use 127.0.0.1:3128?"
(exec 3<>/dev/tcp/127.0.0.1/3128 && printf 'CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n' >&3 && timeout 5 head -c 300 <&3; echo) 2>&1 | head -8
X="openshell sandbox exec --name $NAME --no-tty --no-login-shell --"
echo "== id"; $X id </dev/null
echo "== status"; $X sh -c 'grep -E "^(Uid|CapEff|CapBnd|NoNewPrivs|Seccomp|Seccomp_filters)" /proc/self/status' </dev/null
echo "== processes"; $X sh -c 'for p in /proc/[0-9]*; do printf "%s %s: " ${p#/proc/} $(stat -c %U $p); tr "\0" " " < $p/cmdline; echo; done' </dev/null
echo "== net devices"; $X cat /proc/net/dev </dev/null
echo "== routes"; $X cat /proc/net/route </dev/null
echo "== resolv.conf"; $X cat /etc/resolv.conf </dev/null
echo "== env (names only, values for proxy/ssl/cert)"; $X sh -c 'env | grep -iE "proxy|ssl|cert|openshell" || echo none' </dev/null
echo "== probes"; $X python3 -c "$(cat "$HERE/probe.py")" </dev/null
sleep 3
echo "== OCSF events"; openshell logs $NAME --source sandbox -n 2000 --color never | grep -E 'ocsf' | cut -c1-300 | tail -80
echo "== non-OCSF sandbox log (head)"; openshell logs $NAME --source sandbox -n 2000 --color never | grep -v ocsf | head -40 | cut -c1-260
echo "== gateway log (head)"; openshell logs $NAME --source gateway -n 400 --color never | head -25 | cut -c1-260
echo "== pending rule proposals"; openshell rule get $NAME --status pending 2>&1 | head -20
openshell sandbox delete $NAME >/dev/null 2>&1; echo "== deleted $NAME"
