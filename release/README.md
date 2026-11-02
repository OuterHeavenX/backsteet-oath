# Backstreet Oath: release builds

Built with Godot 4.7.2-stable.

## 1.1.0-rc1: visual upgrade (recommended)
Built from branch `claude/visual-upgrade`. The game is redrawn as inked, cel-shaded 2D at 2× density, and includes
the rc4 audio fix. See `docs/visual/UPGRADE_REPORT.md` on that branch.

| File | What |
|---|---|
| `backstreet-oath-v1.1.0-rc1-web.zip` | HTML5 build, `index.html` at the archive root. Upload to itch.io as an HTML game: viewport 1280×720, SharedArrayBuffer off. |
| `backstreet-oath-v1.1.0-rc1-linux-x86_64.zip` | Linux x86_64 / Steam Deck native. Run `BackstreetOath/start.sh`. |
| `backstreet-oath-v1.1.0-rc1-windows-x86_64.zip` | Windows x86_64 (built; not run-tested). |
| `backstreet-oath-v1.1.0-rc1-source.zip` | Full source (git archive). |
| `itch/` | v1.1 cover (630×500), key art, and 8 gameplay screenshots at native 1280×720. |
| `SHA256SUMS-1.1.0-rc1.txt` | Checksums. |

## 1.0.0-rc4: original pixel-art build with the web audio fix
Built from branch `claude/backstreet-oath-build`. Same files with `-1.0.0-rc4-` in the name; checksums are in
`SHA256SUMS-1.0.0-rc4.txt`.

See README.md, ITCH_PAGE.md and KNOWN_ISSUES.md on the source branches.
