#!/usr/bin/env python3
"""Exports all platforms with Godot and writes versioned release zips + itch assets.

Usage: python3 tools/package.py [version] [--no-export]
Outputs (release/):
  backstreet-oath-v<ver>-web.zip              index.html + files at the archive root (itch.io HTML upload)
  backstreet-oath-v<ver>-linux-x86_64.zip     BackstreetOath/ with binary (+x), .pck, start.sh (+x), docs
  backstreet-oath-v<ver>-windows-x86_64.zip   BackstreetOath/ with .exe, .pck, docs
  backstreet-oath-v<ver>-source.zip           git archive of HEAD
  itch/                                       cover, key art, screenshots (copied by --shots)
"""
import os, sys, subprocess, zipfile, stat, hashlib, shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GAME = os.path.join(ROOT, "game")
BUILD = os.path.join(ROOT, "build")
REL = os.path.join(ROOT, "release")
ver = next((a for a in sys.argv[1:] if not a.startswith("--")), "1.0.0-rc1")
GODOT = shutil.which("godot") or "godot"

START_SH = """#!/bin/sh
# Backstreet Oath launcher. Works from any folder, including paths with spaces.
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$HERE" || exit 1
chmod +x "./BackstreetOath.x86_64" 2>/dev/null
exec "./BackstreetOath.x86_64" "$@"
"""

README_TXT = """BACKSTREET OATH {ver}
An original belt-scrolling action RPG. Made with Godot 4.7.2.

Linux / Steam Deck: run ./start.sh (or BackstreetOath.x86_64). See STEAM_DECK.md.
Windows: run BackstreetOath.exe.
Controls: see CONTROLS.md (rebindable in-game).
Saves: Linux ~/.local/share/godot/app_userdata/Backstreet Oath/ ; Windows %APPDATA%\\Godot\\app_userdata\\Backstreet Oath\\
"""

def export(preset, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r = subprocess.run([GODOT, "--headless", "--export-release", preset, path], cwd=GAME, capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not os.path.exists(path):
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit("export failed: " + preset)
    print("exported", preset, "->", path)

def add(z, src, arc, exe=False):
    info = zipfile.ZipInfo.from_file(src, arc)
    mode = 0o755 if exe else 0o644
    info.external_attr = (stat.S_IFREG | mode) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    with open(src, "rb") as f:
        z.writestr(info, f.read(), compresslevel=9)

def add_text(z, arc, text, exe=False):
    info = zipfile.ZipInfo(arc, date_time=__import__("time").localtime()[:6])
    info.external_attr = (stat.S_IFREG | (0o755 if exe else 0o644)) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, text)

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    os.makedirs(REL, exist_ok=True)
    if "--no-export" not in sys.argv:
        subprocess.run([GODOT, "--headless", "--import"], cwd=GAME, capture_output=True, timeout=600)
        export("Web", os.path.join(BUILD, "web", "index.html"))
        export("Linux", os.path.join(BUILD, "linux", "BackstreetOath.x86_64"))
        export("Windows", os.path.join(BUILD, "windows", "BackstreetOath.exe"))
    outs = []
    # web
    web = os.path.join(REL, f"backstreet-oath-v{ver}-web.zip")
    with zipfile.ZipFile(web, "w") as z:
        for f in sorted(os.listdir(os.path.join(BUILD, "web"))):
            if f.startswith("index."):
                add(z, os.path.join(BUILD, "web", f), f)
    outs.append(web)
    docs = ["README.md", "CONTROLS.md", "STEAM_DECK.md", "THIRD_PARTY_NOTICES.md", "KNOWN_ISSUES.md", "CHANGELOG.md"]
    # linux
    lin = os.path.join(REL, f"backstreet-oath-v{ver}-linux-x86_64.zip")
    with zipfile.ZipFile(lin, "w") as z:
        add(z, os.path.join(BUILD, "linux", "BackstreetOath.x86_64"), "BackstreetOath/BackstreetOath.x86_64", exe=True)
        add(z, os.path.join(BUILD, "linux", "BackstreetOath.pck"), "BackstreetOath/BackstreetOath.pck")
        add_text(z, "BackstreetOath/start.sh", START_SH, exe=True)
        add_text(z, "BackstreetOath/README.txt", README_TXT.format(ver=ver))
        for d in docs:
            add(z, os.path.join(ROOT, d), "BackstreetOath/" + d)
    outs.append(lin)
    # windows
    win = os.path.join(REL, f"backstreet-oath-v{ver}-windows-x86_64.zip")
    if os.path.exists(os.path.join(BUILD, "windows", "BackstreetOath.exe")):
        with zipfile.ZipFile(win, "w") as z:
            add(z, os.path.join(BUILD, "windows", "BackstreetOath.exe"), "BackstreetOath/BackstreetOath.exe")
            add(z, os.path.join(BUILD, "windows", "BackstreetOath.pck"), "BackstreetOath/BackstreetOath.pck")
            add_text(z, "BackstreetOath/README.txt", README_TXT.format(ver=ver).replace("\n", "\r\n"))
            for d in docs:
                if d != "STEAM_DECK.md":
                    add(z, os.path.join(ROOT, d), "BackstreetOath/" + d)
        outs.append(win)
    # source
    src = os.path.join(REL, f"backstreet-oath-v{ver}-source.zip")
    subprocess.run(["git", "archive", "--format=zip", f"--prefix=backstreet-oath-v{ver}-source/", "-o", src, "HEAD"], cwd=ROOT, check=True)
    outs.append(src)
    with open(os.path.join(REL, "SHA256SUMS.txt"), "w") as f:
        for o in outs:
            f.write(f"{sha(o)}  {os.path.basename(o)}\n")
    for o in outs:
        print(f"{os.path.getsize(o) / 1e6:8.1f} MB  {os.path.basename(o)}")

if __name__ == "__main__":
    main()
