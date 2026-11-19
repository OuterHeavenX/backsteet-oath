#!/usr/bin/env python3
"""Per-file size of a web export: raw bytes, gzip -6 (what a host that compresses on the fly would send) and the
size of the release zip (deflate -9, as tools/package.py builds it).

Usage: python3 tools/perf/web_sizes.py build/web [--json out.json]
"""
import gzip, io, json, os, sys, zipfile

d = sys.argv[1]
rows = []
zbuf = io.BytesIO()
with zipfile.ZipFile(zbuf, "w") as z:
    for f in sorted(os.listdir(d)):
        if not f.startswith("index."):
            continue
        data = open(os.path.join(d, f), "rb").read()
        rows.append({"file": f, "bytes": len(data), "gzip6_bytes": len(gzip.compress(data, 6))})
        info = zipfile.ZipInfo(f)
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, data, compresslevel=9)
tot = {"bytes": sum(r["bytes"] for r in rows), "gzip6_bytes": sum(r["gzip6_bytes"] for r in rows), "zip_bytes": zbuf.tell()}
print("%-34s %12s %12s" % ("file", "bytes", "gzip -6"))
for r in rows:
    print("%-34s %12d %12d" % (r["file"], r["bytes"], r["gzip6_bytes"]))
print("%-34s %12d %12d" % ("TOTAL", tot["bytes"], tot["gzip6_bytes"]))
print("release zip (deflate -9): %d bytes = %.1f MB" % (tot["zip_bytes"], tot["zip_bytes"] / 1e6))
if "--json" in sys.argv:
    json.dump({"dir": d, "files": rows, "total": tot}, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
