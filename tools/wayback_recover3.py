#!/usr/bin/env python3
"""Parallel Wayback recovery (v3, reboot-safe).

Writes recovered files DIRECTLY into the git working tree and keeps all
state under ~/.cache/yays-recovery so a reboot costs nothing.

4 workers + global rate limiter + collective freeze on 429/5xx (community
guidance: concurrency >=4 / bursts trigger 15-60 min IP blocks)."""
import os, sys, json, time, threading, subprocess, urllib.parse, urllib.request

W = "/home/takano32/.cache/yays-recovery"
ROOT = "/home/takano32/GitHub/yays"
STATE = W + "/recover_state.jsonl"
UA = {"User-Agent": "yays-archive-recovery/3.0 (contact takano32@gmail.com)"}
SOFT404 = b"Amusement BiG-NET"
CUTOFF = "20190101000000"
WORKERS = 4
MIN_INTERVAL = 0.4

PRIORITY = ["reviews/", "library/", "gallery/", "img/", "", "cgi-bin/newinfo/",
            "cgi-bin/paintbbs", "cgi-bin/paint/", "cgi-bin/anthologys/",
            "cgi-bin/album", "cgi-bin/relaybbs/", "cgi-bin/linkmng/",
            "cgi-bin/resbbs2/", "cgi-bin/noteky/", "cgi-bin/resbbs4a/"]

def url_to_rel(u, mime):
    p = urllib.parse.urlparse(u)
    path = urllib.parse.unquote(p.path)
    if not path.startswith("/~yays"):
        raise ValueError(u)
    rel = path[len("/~yays"):].lstrip("/")
    if rel == "" or rel.endswith("/"):
        rel += "index.html"
    if p.query:
        rel = rel + "_" + p.query.replace("&", "_").replace("=", "-")
    if "html" in mime and not rel.lower().endswith((".html", ".htm")):
        rel += ".html"
    if rel.startswith(".") or "/../" in rel or rel.startswith("tools/"):
        raise ValueError(u)
    return rel

def prio(rel):
    for i, p in enumerate(PRIORITY):
        if p and rel.startswith(p):
            return i
    if "/" not in rel:
        return PRIORITY.index("")
    return len(PRIORITY)

snaps = {}
for line in open(W + "/cdx_snapshots.txt"):
    parts = line.split()
    if len(parts) >= 3 and parts[2] == "200":
        snaps.setdefault(parts[0], []).append(parts[1])
for k in snaps:
    snaps[k] = sorted(set(snaps[k]))

done = set()
if os.path.exists(STATE):
    for line in open(STATE):
        try:
            done.add(json.loads(line)["urlkey"])
        except Exception:
            pass

work = []
seen_rel = set()
for line in open(W + "/cdx_all.txt"):
    parts = line.split()
    if len(parts) < 6:
        continue
    urlkey, _ts, orig, mime = parts[0], parts[1], parts[2], parts[3]
    try:
        rel = url_to_rel(orig, mime)
    except ValueError:
        continue
    cands = [rel] + ([rel + ".html"] if not rel.lower().endswith((".html", ".htm")) else [])
    if any(os.path.exists(os.path.join(ROOT, c)) for c in cands):
        continue
    if urlkey in done or rel in seen_rel:
        continue
    seen_rel.add(rel)
    work.append((prio(rel), rel, urlkey, orig, mime))
work.sort()
total = len(work)
print(f"work items: {total} (already done: {len(done)})", flush=True)

rate_lock = threading.Lock()
freeze_until = [0.0]
last_req = [0.0]
state_lock = threading.Lock()
state_fh = open(STATE, "a")
counts = {"ok": 0, "miss": 0, "n": 0}
work_lock = threading.Lock()
queue = list(work)

def paced_fetch(url):
    while True:
        with rate_lock:
            now = time.time()
            wait = max(freeze_until[0] - now, last_req[0] + MIN_INTERVAL - now, 0)
            if wait == 0:
                last_req[0] = now
        if wait == 0:
            break
        time.sleep(min(wait, 5))
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.headers.get("Content-Type", "")

def fetch_retry(url):
    err = "retries exhausted"
    for attempt in range(5):
        try:
            return paced_fetch(url), ""
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                wait = int(e.headers.get("Retry-After") or 0) or (60 * (attempt + 1))
                with rate_lock:
                    freeze_until[0] = max(freeze_until[0], time.time() + wait)
                print(f"  throttled ({e.code}), all workers frozen {wait}s", flush=True)
                continue
            return None, f"HTTP {e.code}"
        except Exception as e:
            err = str(e)[:80]
            time.sleep(2)
    return None, err

def process(item):
    _, rel, urlkey, orig, mime = item
    tslist = snaps.get(urlkey) or []
    pre = [t for t in tslist if t < CUTOFF]
    post = [t for t in tslist if t >= CUTOFF]
    err = "no snapshots"
    for ts in (list(reversed(pre)) + list(reversed(post)))[:6]:
        got, ferr = fetch_retry(f"https://web.archive.org/web/{ts}id_/{orig}")
        if got is None:
            err = ferr
            continue
        data, ctype = got
        htmlish = "html" in mime or "html" in ctype
        if htmlish and SOFT404 in data:
            err = "soft404 capture"
            continue
        if htmlish and (b"Wayback Machine" in data[:2048] and b"excluded" in data):
            err = "wayback excluded"
            continue
        dest = os.path.join(ROOT, rel)
        if os.path.isdir(dest):
            dest = os.path.join(dest, "index.html")
            rel = rel + "/index.html"
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(data)
        if htmlish:
            enc = subprocess.run(["nkf", "--guess", dest],
                                 capture_output=True, text=True).stdout
            if any(k in enc for k in ("Shift_JIS", "CP932", "EUC-JP", "ISO-2022-JP")):
                subprocess.run(["nkf", "-w", "-Lu", "--overwrite", dest])
            subprocess.run(["sed", "-i", "-E",
                "s/charset=(\"?)(shift_jis|x-sjis|shift-jis|euc-jp|iso-2022-jp)/charset=\\1utf-8/Ig",
                dest])
        return {"urlkey": urlkey, "rel": rel, "orig": orig, "ts": ts, "status": "ok"}
    return {"urlkey": urlkey, "rel": rel, "orig": orig, "status": "miss", "err": err}

def worker():
    while True:
        with work_lock:
            if not queue:
                return
            item = queue.pop(0)
        rec = process(item)
        with state_lock:
            state_fh.write(json.dumps(rec) + "\n")
            state_fh.flush()
            counts[rec["status"]] += 1
            counts["n"] += 1
            if counts["n"] % 25 == 0:
                print(f"[{counts['n']}/{total}] ok={counts['ok']} miss={counts['miss']}",
                      flush=True)

open(W + "/recover3.pid", "w").write(str(os.getpid()))
threads = [threading.Thread(target=worker, daemon=True) for _ in range(WORKERS)]
for t in threads:
    t.start()
    time.sleep(0.7)
for t in threads:
    t.join()
print(f"DONE ok={counts['ok']} miss={counts['miss']}", flush=True)
