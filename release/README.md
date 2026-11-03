# Backstreet Oath: release builds

Built with Godot 4.7.2-stable.

## 1.3.0-rc1: living, more real backgrounds (recommended)
Built from branch `claude/visual-upgrade` (also merged to `main`). This build adds:
- living streets: clouds, windows, passersby, pigeons, traffic, trains, swaying cloth, water, light shafts and neon;
- a realism pass on all 33 rooms;
- a subtle colour grade with bloom.

It also includes everything from 1.2 (the Underline, the ladder, the side jobs, New Game+) and the 1.1 visual
upgrade.

| File | What |
|---|---|
| `backstreet-oath-v1.3.0-rc1-web.zip` | HTML5 build, `index.html` at the archive root. Upload to itch.io as an HTML game: viewport 1280×720, SharedArrayBuffer off. |
| `backstreet-oath-v1.3.0-rc1-linux-x86_64.zip` | Linux x86_64 / Steam Deck native. Run `BackstreetOath/start.sh`. |
| `backstreet-oath-v1.3.0-rc1-windows-x86_64.zip.part0` + `.part1` | Windows x86_64 (built; not run-tested). **Split in two because the zip (102 MB) is over GitHub's 100 MB file limit.** Join them first. On Windows: `copy /b backstreet-oath-v1.3.0-rc1-windows-x86_64.zip.part0 + backstreet-oath-v1.3.0-rc1-windows-x86_64.zip.part1 backstreet-oath-v1.3.0-rc1-windows-x86_64.zip`. On Linux/macOS: `cat *.zip.part0 *.zip.part1 > backstreet-oath-v1.3.0-rc1-windows-x86_64.zip`. The joined file matches the checksum in `SHA256SUMS-1.3.0-rc1.txt`. |
| `backstreet-oath-v1.3.0-rc1-source.zip` | Full source (git archive). |
| `itch/` | Cover (630×500), key art, and 10 gameplay screenshots at native 1280×720 (refreshed for 1.3). |

## 1.0.0-rc4: original pixel-art build with the web audio fix
Built from branch `claude/backstreet-oath-build`. Same files with `-1.0.0-rc4-` in the name; checksums are in
`SHA256SUMS-1.0.0-rc4.txt`.

See README.md, ITCH_PAGE.md and KNOWN_ISSUES.md on the source branches.
