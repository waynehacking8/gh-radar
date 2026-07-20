"""Transport layer: thin clients for the network services. Every call degrades to
None/empty on failure so a single outage never propagates up and breaks the run."""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from . import config

FC_SCRAPE = "https://api.firecrawl.dev/v2/scrape"


def http_get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": config.UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def gh_api(path):
    """api.github.com with token if available. Parsed JSON, or None on any error."""
    headers = {"Accept": "application/vnd.github+json"}
    if config.GH_TOKEN:
        headers["Authorization"] = f"Bearer {config.GH_TOKEN}"
    try:
        return json.loads(http_get(f"https://api.github.com{path}", headers))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("  ! github api rate-limited (set GITHUB_TOKEN to fix)", file=sys.stderr)
        else:
            print(f"  ! github api {e.code} on {path}", file=sys.stderr)
        return None
    except Exception as e:  # noqa: BLE001
        print(f"  ! github api error on {path}: {e}", file=sys.stderr)
        return None


def firecrawl(endpoint, payload):
    """Firecrawl (free + keyless; FIRECRAWL_API_KEY raises limits a lot). Retries on
    429 with backoff (honouring Retry-After). -> data dict / None. Never raises."""
    retries = 3
    headers = {"User-Agent": config.UA, "Content-Type": "application/json"}
    fkey = os.environ.get("FIRECRAWL_API_KEY")
    if fkey:
        headers["Authorization"] = f"Bearer {fkey}"
    body = json.dumps(payload).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(endpoint, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
            return data.get("data") if data.get("success") else None
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = min(int(e.headers.get("Retry-After") or 0) or 5 * (attempt + 1), 30)
                print(f"  i firecrawl 429 — backing off {wait}s "
                      f"(set FIRECRAWL_API_KEY to raise limits)", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"  ! firecrawl {endpoint.rsplit('/', 1)[-1]}: {e}", file=sys.stderr)
            return None
        except Exception as e:  # noqa: BLE001
            print(f"  ! firecrawl {endpoint.rsplit('/', 1)[-1]}: {e}", file=sys.stderr)
            return None
    return None


def scrape_md(url):
    """Scrape one URL to markdown. '' on failure. maxAge lets Firecrawl serve a
    recent cached scrape (faster + far cheaper than a fresh crawl)."""
    data = firecrawl(FC_SCRAPE, {"url": url, "formats": ["markdown"],
                                 "maxAge": 14_400_000})   # accept ≤4h-old cache
    return (data.get("markdown") or "").replace("\\", "") if isinstance(data, dict) else ""


def claude_json(prompt, want="object", model="sonnet", timeout=240):
    """Run `claude -p` and parse a JSON object/array from its reply. Returns the
    parsed value, or None if claude is absent/unauthenticated/times out/malformed."""
    cli = shutil.which("claude")
    if not cli:
        return None
    try:
        proc = subprocess.run(
            [cli, "-p", "--output-format", "json", "--model", model],
            input=prompt, capture_output=True, text=True, timeout=timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"claude exited {proc.returncode}: {proc.stderr.strip()[:200]}")
        text = json.loads(proc.stdout).get("result", "") or ""
        m = re.search(r"\{.*\}" if want == "object" else r"\[.*\]", text, re.S)
        if not m:
            raise ValueError("no JSON in model output")
        return json.loads(m.group(0))
    except Exception as e:  # noqa: BLE001
        print(f"  ! claude call failed ({e})", file=sys.stderr)
        return None
