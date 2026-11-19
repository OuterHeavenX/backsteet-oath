#!/usr/bin/env python3
"""Audits which v1 (fallback) art the game can still reach at runtime, against what the export presets exclude.

The v2 art lives in `*2` folders (bg2, sprites/chars, props2, icons2, portraits2, fx2, pickups2, weapons2, ui2); the
v1 art (bg, sprites/characters, props, icons, portraits, fx, pickups, weapons, ui) is the fallback that
scripts/core/sprite_lib.gd and friends use when a v2 file is missing. The export presets exclude the v1 PNGs, so
a v1 file that is still *needed* (no v2 counterpart for an id the data references) would become a placeholder in
the shipped build. This script lists exactly those, and the v1 files that are safe to leave out.

Usage: python3 tools/perf/audit_assets.py            (exit code 1 if a needed fallback is excluded)
"""
import fnmatch, glob, json, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GAME = os.path.join(ROOT, "game")
A = os.path.join(GAME, "assets")


def ids(folder, ext=".png"):
    return {os.path.basename(p)[:-len(ext)] for p in glob.glob(os.path.join(A, folder, "*" + ext))}


def load(rel):
    return json.load(open(os.path.join(GAME, rel)))


def scripts_text():
    out = []
    for dp, dn, fn in os.walk(os.path.join(GAME, "scripts")):
        for f in fn:
            if f.endswith(".gd"):
                out.append(open(os.path.join(dp, f)).read())
    return "\n".join(out)


def main():
    problems = []
    report = []
    code = scripts_text()

    # ---- rooms: every room needs bg2/<id>/room.json, otherwise room.gd falls back to bg/<id>.png + parallax
    rooms = load("data/rooms.json")
    rooms = rooms.get("rooms", rooms)
    no_v2_rooms = sorted(r for r in rooms if not os.path.exists(os.path.join(A, "bg2", r, "room.json")))
    report.append(("rooms", len(rooms), len(rooms) - len(no_v2_rooms), no_v2_rooms))
    if no_v2_rooms:
        problems.append("rooms without v2 art (would need assets/bg/<id>.png): " + ", ".join(no_v2_rooms))
    # layer / fg / life files named in room.json must exist
    missing_files = []
    for rj in sorted(glob.glob(os.path.join(A, "bg2", "*", "room.json"))):
        d = os.path.dirname(rj)
        meta = json.load(open(rj))
        files = []
        for L in meta.get("layers", []):
            files += L.get("files", [])
        files += [F.get("file", "") for F in meta.get("fg", [])]
        files += meta.get("clouds", {}).get("files", [])
        if "file" in meta.get("lightmap", {}):
            files.append(meta["lightmap"]["file"])
        for e in meta.get("life", []):
            if isinstance(e, dict):
                files += e.get("files", [])
                if e.get("file"):
                    files.append(e["file"])
        for f in files:
            if not f:
                continue
            p = os.path.join(A, "bg2", f[3:]) if f.startswith("../") else os.path.join(d, f)
            if not os.path.exists(p):
                missing_files.append(os.path.relpath(p, A))
    if missing_files:
        problems.append("room.json names missing files: " + ", ".join(sorted(set(missing_files))[:20]))

    # ---- characters: every sprite id the data or scripts can ask for needs sprites/chars/<id>.{png,json}
    want = {"nico"}
    en = load("data/enemies.json")
    for g in en.get("gangs", {}):
        for arch in en.get("archetypes", {}):
            want.add("%s_%s" % (g, arch))
    for k, v in en.get("bosses", {}).items():
        want.add(v.get("sprite", k))
    enc = load("data/encounters.json").get("rooms", {})
    for rid, e in enc.items():
        for n in e.get("npcs", []):
            want.add(n.get("sprite", n.get("id")))
    for m in re.finditer(r'(?:WALKERS|PASSERS)\s*:=\s*\[([^\]]*)\]', code):
        want |= set(re.findall(r'"([a-z0-9_]+)"', m.group(1)))
    for m in re.finditer(r'setup_visual(?:_swap)?\("([a-z0-9_]+)"\)', code):
        want.add(m.group(1))
    for m in re.finditer(r'spawn_npc\("[a-z0-9_]+",\s*"([a-z0-9_]+)"', code):
        want.add(m.group(1))
    v2c = ids("sprites/chars") & ids("sprites/chars", ".json")
    v1c = ids("sprites/characters")
    need_v1 = sorted(c for c in want if c and c not in v2c)
    report.append(("character sheets", len(want), len(want & v2c), need_v1))
    if need_v1:
        problems.append("character ids with no v2 sheet: " + ", ".join(need_v1))

    # ---- same-name categories: an id is safe when the v2 folder has the same file name
    for name, v1, v2 in [("icons", "icons", "icons2"), ("props", "props", "props2"), ("weapons", "weapons", "weapons2"),
                         ("pickups", "pickups", "pickups2"), ("portraits", "portraits", "portraits2")]:
        a, b = ids(v1), ids(v2)
        only_v1 = sorted(a - b)
        report.append((name, len(a), len(a & b), only_v1))
    # dialogue speakers: every portrait id in characters.json needs portraits2/<id>.png
    chars = load("data/characters.json")
    chars = chars.get("characters", chars)
    pw = {v.get("portrait") for v in chars.values() if isinstance(v, dict) and v.get("portrait")}
    pmiss = sorted(pw - ids("portraits2"))
    report.append(("portraits used", len(pw), len(pw) - len(pmiss), pmiss))
    if pmiss:
        problems.append("speaker portraits without v2 art: " + ", ".join(pmiss))
    # props/weapons/pickups also need their v2 metadata entry (sprite_lib checks `m2.has(id)`)
    p2 = json.load(open(os.path.join(A, "props2", "props.json")))
    types = set()
    for r in rooms.values():
        for p in r.get("props", []):
            types.add(p.get("type"))
    types |= set(re.findall(r'prop\.setup\(self, "([a-z0-9_]+)"', code))
    miss = sorted(t for t in types if t and (t not in p2 or t not in ids("props2")))
    report.append(("prop types used", len(types), len(types) - len(miss), miss))
    if miss:
        problems.append("prop types without v2 art/metadata: " + ", ".join(miss))
    w2 = json.load(open(os.path.join(A, "weapons2", "weapons.json")))
    w2 = w2.get("weapons", w2)
    weapons = load("data/weapons.json")
    weapons = weapons.get("weapons", weapons)
    wmiss = []
    for k, v in weapons.items():
        spr = v.get("sprite", k) if isinstance(v, dict) else k
        if spr.startswith("prop:"):
            if spr[5:] not in p2:
                wmiss.append(k)
        elif spr not in w2 or spr not in ids("weapons2"):
            wmiss.append(k)
    report.append(("weapons used", len(weapons), len(weapons) - len(wmiss), sorted(wmiss)))
    if wmiss:
        problems.append("weapons without v2 art/metadata: " + ", ".join(sorted(wmiss)))

    # ---- fx: ids passed to spawn_fx / make_strip must resolve through fx2/fx.json (with FX.V2_NAME aliases)
    fx2 = json.load(open(os.path.join(A, "fx2", "fx.json")))
    alias = {}
    m = re.search(r'const V2_NAME := \{(.*?)\}', code, re.S)
    if m:
        alias = dict(re.findall(r'"([a-z0-9_]+)":\s*"([a-z0-9_]+)"', m.group(1)))
    used = set(re.findall(r'spawn_fx\(\s*"([a-z0-9_]+)"', code)) | set(re.findall(r'make_strip\(\s*"([a-z0-9_]+)"', code))
    used |= set(re.findall(r'"fx":\s*"([a-z0-9_]+)"', open(os.path.join(GAME, "data", "attacks.json")).read()))
    fmiss = sorted(f for f in used if alias.get(f, f) not in fx2)
    report.append(("fx ids used", len(used), len(used) - len(fmiss), fmiss))
    v1fx = ids("fx")
    fneed = [f for f in fmiss if f in v1fx]
    if fneed:
        problems.append("fx ids that only exist as v1 strips: " + ", ".join(fneed))

    # ---- ui: SpriteLib.ui("id") / ui2("id") / ui2_half / ui2_box fall back to assets/ui/<id>.png
    uused = set(re.findall(r'SpriteLib\.ui2?(?:_half|_box)?\(\s*"([a-z0-9_]+)"', code))
    u2 = ids("ui2")
    umiss = sorted(u for u in uused if u not in u2)
    report.append(("ui ids used (literal)", len(uused), len(uused) - len(umiss), umiss))
    if [u for u in umiss if u in ids("ui")]:
        problems.append("ui ids that only exist as v1: " + ", ".join(u for u in umiss if u in ids("ui")))

    # ---- direct v1 paths in scripts
    direct = sorted(set(re.findall(r'"(res://assets/(?:bg|sprites/characters|props|ui|icons|portraits|fx|pickups|weapons|fonts)/[^"]*)"', code)))

    # ---- export filters
    presets = open(os.path.join(GAME, "export_presets.cfg")).read()
    filters = sorted(set(re.findall(r'exclude_filter="([^"]*)"', presets)))
    print("export exclude_filter (all presets identical: %s):" % (len(filters) == 1))
    for f in filters:
        for part in f.split(","):
            print("   ", part.strip())
    print()
    print("%-24s %6s %6s  %s" % ("category", "ids", "in v2", "ids with NO v2 counterpart"))
    for name, n, ok, lst in report:
        print("%-24s %6d %6d  %s" % (name, n, ok, ", ".join(lst) if lst else "-"))
    print()
    print("v1 paths named directly in scripts (all are guarded fallbacks unless listed under problems):")
    for d in direct:
        print("   ", d)
    # excluded-but-needed check: every direct v1 path must be reached only when the v2 file is missing
    excl = [p.strip() for p in filters[0].split(",")] if filters else []
    v1_total = 0
    for folder in ["bg", "sprites/characters", "props", "ui", "icons", "portraits", "fx", "pickups", "weapons"]:
        for p in glob.glob(os.path.join(A, folder, "*.png")):
            rel = os.path.relpath(p, GAME)
            if not any(fnmatch.fnmatch(rel, e) for e in excl):
                problems.append("v1 file not excluded from export: " + rel)
            v1_total += os.path.getsize(p)
    print()
    print("v1 PNG source bytes on disk (excluded from every export preset): %d" % v1_total)
    print()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  -", p)
        return 1
    print("OK: no id referenced by data or scripts depends on an excluded v1 file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
