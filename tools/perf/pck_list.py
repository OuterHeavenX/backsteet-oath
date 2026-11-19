#!/usr/bin/env python3
"""Lists what is inside an exported Godot 4 .pck (unencrypted), grouped by folder and type, largest files first.

Usage: python3 tools/perf/pck_list.py build/web/index.pck [--top 30] [--json out.json]
Imported resources are attributed to their source folder through the .import remap files inside the pack.
"""
import collections, json, re, struct, sys


def read_pck(path):
    f = open(path, "rb")
    magic = f.read(4)
    if magic != b"GDPC":
        raise SystemExit("not a Godot pck (or embedded/encrypted): " + path)
    fmt, vmaj, vmin, vpatch = struct.unpack("<4I", f.read(16))
    flags, files_base = 0, 0
    if fmt >= 2:
        flags, files_base = struct.unpack("<IQ", f.read(12))
    dir_off = 0
    if fmt >= 3:
        (dir_off,) = struct.unpack("<Q", f.read(8))
    f.read(16 * 4)
    if fmt >= 3 and dir_off:
        f.seek(dir_off)
    (n,) = struct.unpack("<I", f.read(4))
    out = []
    for _ in range(n):
        (sl,) = struct.unpack("<I", f.read(4))
        name = f.read(sl).rstrip(b"\x00").decode("utf-8")
        ofs, size = struct.unpack("<QQ", f.read(16))
        f.read(16)
        if fmt >= 2:
            f.read(4)
        out.append((name, files_base + ofs, size))
    return f, out, (fmt, vmaj, vmin, vpatch)


def main():
    path = sys.argv[1]
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 30
    f, files, ver = read_pck(path)
    names = {n if n.startswith("res://") else "res://" + n: (o, s) for n, o, s in files}
    # map imported payloads (.godot/imported/x.ctex ...) back to their source asset
    src_of = {}
    for n, (o, s) in names.items():
        if n.endswith(".import"):
            f.seek(o)
            txt = f.read(s).decode("utf-8", "replace")
            for m in re.finditer(r'path(?:\.[a-z0-9_]+)?="(res://\.godot/imported/[^"]+)"', txt):
                src_of[m.group(1)] = n[:-7]
    groups = collections.defaultdict(lambda: [0, 0])
    rows = []
    for n, (o, s) in names.items():
        src = src_of.get(n, n)
        rel = src[6:]
        parts = rel.split("/")
        if parts[0] == "assets" and len(parts) > 2:
            g = "assets/" + parts[1] + ("/" + parts[2] if parts[1] in ("sprites", "audio") and len(parts) > 3 else "")
        elif parts[0] == ".godot":
            g = ".godot (other)"
        else:
            g = parts[0] if len(parts) > 1 else "(root)"
        groups[g][0] += s
        groups[g][1] += 1
        rows.append((s, rel + ("" if src == n else "  [imported]")))
    total = sum(s for s, _ in rows)
    print("%s: pack format %d, Godot %d.%d.%d, %d files, %.2f MiB of file data" % (path, ver[0], ver[1], ver[2], ver[3], len(rows), total / 1048576.0))
    print("%-28s %6s %12s %7s" % ("group", "files", "bytes", "share"))
    for g, (b, c) in sorted(groups.items(), key=lambda x: -x[1][0]):
        print("%-28s %6d %12d %6.1f%%" % (g, c, b, 100.0 * b / total))
    print()
    for s, n in sorted(rows, reverse=True)[:top]:
        print("%10d  %s" % (s, n))
    if "--json" in sys.argv:
        out = sys.argv[sys.argv.index("--json") + 1]
        json.dump({"pack": path, "files": len(rows), "bytes": total,
                   "groups": {g: {"bytes": b, "files": c} for g, (b, c) in groups.items()},
                   "largest": [{"bytes": s, "file": n} for s, n in sorted(rows, reverse=True)[:200]]}, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
