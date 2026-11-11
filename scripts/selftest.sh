#!/usr/bin/env bash
# Run the page's built-in self-test in headless Chrome: once at desktop width and
# once inside a 375px-wide frame (scripts/phone.html).
# Usage (Git Bash on Windows, from anywhere):  scripts/selftest.sh
# Set CHROME to your browser binary if it is somewhere else.
set -u
CHROME=${CHROME:-"/c/Program Files/Google/Chrome/Application/chrome.exe"}
cd "$(dirname "$0")/.."
HERE=$(pwd -W 2>/dev/null) || HERE=$(pwd)
BASE="file:///${HERE// /%20}"
PROF=$(mktemp -d)
rc=0
for run in "1440,900 index.html" "900,900 scripts/phone.html"; do
  size=${run%% *}; URL="$BASE/${run##* }?selftest=1"
  out=$("$CHROME" --headless=new --disable-gpu --no-first-run --user-data-dir="$(cygpath -w "$PROF" 2>/dev/null || echo "$PROF")" --window-size=$size --virtual-time-budget=8000 --dump-dom "$URL" 2>/dev/null | grep -o 'SELFTEST {.*}' | head -1 | sed 's/&quot;/"/g; s/&gt;/>/g; s/&lt;/</g; s/&amp;/\&/g')
  echo "[${run##* }] ${out:-NO SELFTEST OUTPUT (script error before the test ran?)}"
  case "$out" in *'"ok":true'*) ;; *) rc=1 ;; esac
done
rm -rf "$PROF"
exit $rc
