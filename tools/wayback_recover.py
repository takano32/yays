#!/usr/bin/env python3
"""Recover content lost from the live server using the Wayback Machine.

Inputs (in scratchpad dir):
  cdx_all.txt       urlkey, first-200-timestamp, original, mimetype, 200, length
  cdx_snapshots.txt urlkey, timestamp, 200          (all 200 captures)

Snapshot policy per URL: newest capture before 2019 (pre soft-404 era),
falling back to progressively older ones; verify HTML payloads are not the
BiG-NET soft-404 template or a Wayback error page.

State: recover_state.jsonl (one JSON per attempted URL) — resumable.
"""
import os, sys, json, time, subprocess, urllib.parse, urllib.request

S = "/tmp/claude-1000/-home-takano32-GitHub-yays/c47f8e8d-a0a6-4acf-8cd7-b92ff5ea5b25/scratchpad"
ROOT = S + "/mirror/www14.big.or.jp/~yays"
STATE = S + "/recover_state.jsonl"
UA = {"User-Agent": "yays-archive-recovery/1.0 (contact takano32@gmail.com)"}
SOFT404 = b"Amusement BiG-NET"
CUTOFF = "20190101000000"
LIMIT = None
if "--limit" in sys.argv:
    LIMIT = int(sys.argv[sys.argv.index("--limit") + 1])

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
        rel += ".html"   # match wget --adjust-extension convention
    return rel

def prio(rel):
    best = len(PRIORITY)
    for i, p in enumerate(PRIORITY):
        if p and rel.startswith(p):
            return i
    if "/" not in rel:
        return PRIORITY.index("")
    return best

# --- build work list -------------------------------------------------------
snaps = {}
for line in open(S + "/cdx_snapshots.txt"):
    parts = line.split()
    if len(parts) >= 3 and parts[2] == "200":
        snaps.setdefault(parts[0], []).append(parts[1])
for k in snaps:
    snaps[k] = sorted(set(snaps[k]))

done = set()
if os.path.exists(STATE):
    for line in open(STATE):
        try:
            rec = json.loads(line)
            done.add(rec["urlkey"])
        except Exception:
            pass

work = []
seen_rel = set()
for line in open(S + "/cdx_all.txt"):
    parts = line.split()
    if len(parts) < 6:
        continue
    urlkey, _ts, orig, mime = parts[0], parts[1], parts[2], parts[3]
    try:
        rel = url_to_rel(orig, mime)
    except ValueError:
        continue
    cands = [rel]
    if not rel.lower().endswith((".html", ".htm")):
        cands.append(rel + ".html")
    if any(os.path.exists(os.path.join(ROOT, c)) for c in cands):
        continue
    if urlkey in done or rel in seen_rel:
        continue
    seen_rel.add(rel)
    work.append((prio(rel), rel, urlkey, orig, mime))
work.sort()
if LIMIT:
    work = work[:LIMIT]
print(f"work items: {len(work)} (already done: {len(done)})", flush=True)

# --- fetch loop ------------------------------------------------------------
def pick_candidates(tslist):
    pre = [t for t in tslist if t < CUTOFF]
    post = [t for t in tslist if t >= CUTOFF]
    # newest pre-2019 first, then older pre-2019, then post-2019 newest-first
    return list(reversed(pre)) + list(reversed(post))

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.headers.get("Content-Type", "")

state_fh = open(STATE, "a")
ok = miss = 0
for n, (_, rel, urlkey, orig, mime) in enumerate(work, 1):
    tslist = snaps.get(urlkey) or []
    saved = False
    err = ""
    for ts in pick_candidates(tslist)[:6]:
        wurl = f"https://web.archive.org/web/{ts}id_/{orig}"
        for attempt in range(5):
            try:
                data, ctype = fetch(wurl)
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 503, 502, 504):
                    wait = int(e.headers.get("Retry-After") or 0) or (20 * 2 ** attempt)
                    print(f"  throttled ({e.code}), sleeping {wait}s", flush=True)
                    time.sleep(wait)
                    continue
                err = f"HTTP {e.code}"
                data = None
                break
            except Exception as e:
                err = str(e)[:80]
                data = None
                time.sleep(3)
                break
        if data is None:
            continue
        htmlish = "html" in mime or "html" in ctype
        if htmlish and SOFT404 in data:
            err = "soft404 capture"
            time.sleep(1.0)
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
        state_fh.write(json.dumps({"urlkey": urlkey, "rel": rel, "orig": orig,
                                   "ts": ts, "status": "ok"}) + "\n")
        state_fh.flush()
        ok += 1
        saved = True
        break
    if not saved:
        state_fh.write(json.dumps({"urlkey": urlkey, "rel": rel, "orig": orig,
                                   "status": "miss", "err": err}) + "\n")
        state_fh.flush()
        miss += 1
    if n % 25 == 0:
        print(f"[{n}/{len(work)}] ok={ok} miss={miss}", flush=True)
    time.sleep(1.0)
print(f"DONE ok={ok} miss={miss}", flush=True)
