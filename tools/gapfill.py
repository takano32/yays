#!/usr/bin/env python3
"""Iteratively fetch files that are referenced by the mirror but missing
locally (wget missed links in comments / odd markup). Repeats until no new
file can be fetched. Newly fetched HTML is converted to UTF-8 via nkf and
its charset meta rewritten, matching the rest of the tree."""
import os, re, sys, time, subprocess, urllib.parse, urllib.request

root = os.path.abspath(sys.argv[1])
BASE = "https://www14.big.or.jp/~yays/"
UA = {"User-Agent": "Mozilla/5.0 (mirror-gapfill; contact takano32@gmail.com)"}

attr_re = re.compile(
    r"""(?:href|src|background)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
    re.IGNORECASE)
comment_re = re.compile(rb"<!--.*?-->", re.DOTALL)

def extract_targets():
    """Return {local_path_to_fetch} for internal links whose target is missing."""
    missing = {}
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.lower().endswith((".html", ".htm", ".shtml")):
                continue
            fpath = os.path.join(dirpath, name)
            raw = open(fpath, "rb").read()
            # scan both commented and uncommented content: wget missed the
            # commented ones, but they are real, reachable URLs we want too?
            # -> NO: keep fidelity, but fetch them only if something outside
            #    a comment ALSO references them. Commented-out links are
            #    invisible in a browser; skip them.
            if "--include-comments" not in sys.argv:
                raw = comment_re.sub(b"", raw)
            text = raw.decode("utf-8", errors="replace")
            for m in attr_re.finditer(text):
                link = next(g for g in m.groups() if g is not None).strip()
                if (not link or link.startswith(("#", "mailto:", "javascript:",
                                                 "data:", "ftp:"))):
                    continue
                if any(c in link for c in "'()<>{}【】\"") or link.startswith("&"):
                    continue  # regex junk from JS or broken markup
                p = urllib.parse.urlparse(link)
                if p.scheme in ("http", "https"):
                    continue  # absolute links handled separately
                path = urllib.parse.unquote(p.path)
                if not path:
                    continue
                if path.startswith("/"):
                    resolved = os.path.normpath(os.path.join(root, path.lstrip("/")))
                else:
                    resolved = os.path.normpath(os.path.join(dirpath, path))
                if not resolved.startswith(root):
                    continue
                if path.endswith("/"):
                    resolved = os.path.join(resolved, "index.html")
                if not os.path.exists(resolved):
                    missing.setdefault(resolved, os.path.relpath(fpath, root))
    return missing

def is_htmlish(path, ctype):
    return ("html" in ctype) or path.lower().endswith((".html", ".htm", ".shtml"))

seen_fail = set()
total_fetched = 0
for round_no in range(1, 11):
    missing = {p: src for p, src in extract_targets().items() if p not in seen_fail}
    if not missing:
        break
    print(f"--- round {round_no}: {len(missing)} missing targets ---")
    fetched = 0
    for resolved, src in sorted(missing.items()):
        rel = os.path.relpath(resolved, root)
        url = BASE + urllib.parse.quote(rel)
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
                ctype = r.headers.get("Content-Type", "")
        except Exception as e:
            print(f"  MISS {rel}  ({getattr(e, 'code', e)})  [from {src}]")
            seen_fail.add(resolved)
            continue
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "wb") as fh:
            fh.write(data)
        if is_htmlish(resolved, ctype):
            enc = subprocess.run(["nkf", "--guess", resolved],
                                 capture_output=True, text=True).stdout
            if any(k in enc for k in ("Shift_JIS", "CP932", "EUC-JP", "ISO-2022-JP")):
                subprocess.run(["nkf", "-w", "-Lu", "--overwrite", resolved])
            subprocess.run(["sed", "-i", "-E",
                "s/charset=(\"?)(shift_jis|x-sjis|shift-jis|euc-jp|iso-2022-jp)/charset=\\1utf-8/Ig",
                resolved])
        print(f"  GOT  {rel}  ({len(data)}b)  [from {src}]")
        fetched += 1
        total_fetched += 1
        time.sleep(0.3)
    if fetched == 0:
        break
print(f"\ntotal fetched: {total_fetched}, unresolvable: {len(seen_fail)}")
