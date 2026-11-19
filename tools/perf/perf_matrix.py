#!/usr/bin/env python3
"""Runs the performance harness (game/tests/perf.gd) over a matrix of configurations and writes JSON + Markdown.

Each (configuration, repeat) is its own Godot process. Repeats are interleaved (all configurations once, then all
again) so slow drift of the machine shows up as run-to-run noise instead of biasing one configuration.

Usage (from the repository root):
  python3 tools/perf/perf_matrix.py --out /tmp/perf/baseline --configs base --repeats 3
  python3 tools/perf/perf_matrix.py --out /tmp/perf/profile  --profile --repeats 3 --seconds 5 \\
      --scenarios kettle_quiet,kettle_combat8,pumpstation_rain,marquee_neon,vault_kowal_dark

Configurations:
  base                 everything on (effects=full, post_fx=on)
  postfx_off           Settings.post_fx = false          (the player's "Colour grade & bloom: Off")
  reduced              Settings.effects = "reduced"      (the player's "Effects: Reduced")
  reduced_postfx_off   both
  no_<system>          PERF_DISABLE=<system> (see game/scripts/core/perf_debug.gd), e.g. no_bloom, no_glows;
                       join several with "+": no_grade+glows
  --profile            = base + no_<system> for every profiled system + the three player-facing presets

Statistics: a shared or virtualised machine has bursts of interference that slow a whole run (seen here as the
same configuration measuring 40 ms and 52 ms minutes apart). For every (configuration, scenario) the summary
therefore reports the BEST run (lowest average frame time = least disturbed) and, as the noise figure, how far
the second-best run is from it. Costs are differences of best runs.

Needs a display: the script wraps Godot in `xvfb-run -a -s "-screen 0 WxHx24"`. Numbers from a software
rasteriser (llvmpipe) are for relative comparison on the same machine only; the renderer is recorded in the output.
"""
import argparse, json, os, shutil, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GAME = os.path.join(ROOT, "game")
PROFILE_SYSTEMS = ["grade", "bloom", "haze", "parallax", "fg", "glows", "lightmap", "rim", "cast", "reflect", "ambient",
                   "life", "clouds", "windows", "lanes", "pigeons", "sway", "water", "signs", "shafts", "passers",
                   "rain", "actor_shader", "combat_fx", "hud"]
PRESETS = {
    "base": {},
    "postfx_off": {"PERF_POSTFX": "off"},
    "reduced": {"PERF_EFFECTS": "reduced"},
    "reduced_postfx_off": {"PERF_EFFECTS": "reduced", "PERF_POSTFX": "off"},
}
# Scenarios in which a switch can have any effect (the room has that system). Others are skipped to save time.
OUTDOOR = ["kettle_quiet", "kettle_combat8", "pumpstation_rain", "marquee_neon"]
APPLIES = {
    "rain": ["pumpstation_rain"],
    "combat_fx": ["kettle_combat8", "pumpstation_rain", "vault_kowal_dark", "boss_rook"],
    "parallax": OUTDOOR, "clouds": OUTDOOR, "windows": OUTDOOR,
    "lanes": ["kettle_quiet", "kettle_combat8", "pumpstation_rain"],
    "pigeons": ["kettle_quiet", "kettle_combat8", "pumpstation_rain"],
    "sway": ["kettle_quiet", "kettle_combat8", "pumpstation_rain"],
    "signs": ["kettle_quiet", "kettle_combat8", "marquee_neon"],
    "shafts": ["vault_kowal_dark"],
    "passers": ["kettle_quiet", "marquee_neon"],
}
ALL_SCENARIOS = ["kettle_quiet", "kettle_combat8", "pumpstation_rain", "marquee_neon", "vault_kowal_dark", "interior_diner",
                 "boss_rook"]


def env_for(config):
    if config in PRESETS:
        return dict(PRESETS[config])
    if config.startswith("no_"):
        return {"PERF_DISABLE": config[3:].replace("+", ",")}
    raise SystemExit("unknown configuration: " + config)


def scenarios_for(config, args):
    want = [s for s in ALL_SCENARIOS if not args.scenarios or any(o in s for o in args.scenarios.split(","))]
    if config.startswith("no_") and config[3:] in APPLIES:
        want = [s for s in want if s in APPLIES[config[3:]]]
    return want


def run_one(config, rep, args):
    out = os.path.join(args.out, "%s.r%d.json" % (config, rep))
    if os.path.exists(out) and not args.force:
        return
    scen = scenarios_for(config, args)
    if not scen:
        return
    env = dict(os.environ)
    env.update(env_for(config))
    env.update({"PERF_SECONDS": str(args.seconds), "PERF_WARMUP": str(args.warmup), "PERF_OUT": out,
                "PERF_LABEL": "%s %s r%d" % (args.label, config, rep), "PERF_SEED": str(args.seed),
                "PERF_ONLY": ",".join(scen)})
    w, h = args.resolution.split("x")
    cmd = ["xvfb-run", "-a", "-s", "-screen 0 %sx%sx24" % (w, h), args.godot, "--resolution", args.resolution,
           "res://tests/perf.tscn"]
    t0 = time.time()
    r = subprocess.run(cmd, cwd=args.game, env=env, capture_output=True, text=True, timeout=args.timeout)
    if not os.path.exists(out):
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit("harness produced no output for " + config)
    errs = [l for l in (r.stdout + r.stderr).splitlines() if "SCRIPT ERROR" in l]
    if errs:
        sys.stderr.write("\n".join(errs[:10]) + "\n")
        raise SystemExit("script errors in " + config)
    print("  %-22s r%d  %5.0fs" % (config, rep, time.time() - t0), flush=True)


def load_runs(args, configs):
    data, meta = {}, None
    for c in configs:
        for rep in range(args.repeats):
            p = os.path.join(args.out, "%s.r%d.json" % (c, rep))
            if not os.path.exists(p):
                continue
            j = json.load(open(p))
            meta = meta or j["meta"]
            for s in j["scenarios"]:
                data.setdefault(c, {}).setdefault(s["scenario"], []).append(s)
    return meta, data


def pick(runs):
    """Best (least disturbed) run, plus the spread of the average frame time across runs."""
    rs = sorted(runs, key=lambda r: r["avg_ms"])
    avgs = [r["avg_ms"] for r in rs]
    return {"best": rs[0], "n": len(rs), "avgs": avgs, "gap": (avgs[1] - avgs[0]) if len(avgs) > 1 else 0.0,
            "worst": avgs[-1]}


def summarise(args, configs):
    meta, data = load_runs(args, configs)
    if not data:
        raise SystemExit("no results in " + args.out)
    scen = [s for s in ALL_SCENARIOS if any(s in data[c] for c in data)]
    picked = {c: {s: pick(data[c][s]) for s in data[c]} for c in data}
    json.dump({"meta": meta, "repeats": args.repeats, "configs": picked}, open(os.path.join(args.out, "summary.json"), "w"), indent=1)

    L = []
    soft = " **Software renderer: not GPU numbers.**" if meta.get("software_renderer") else ""
    L.append("Renderer: `%s` (%s, OpenGL %s), %s, CPU `%s` x%s, window %sx%s px, Godot %s, game %s, debug build: %s.%s" % (
        meta["adapter"], meta["rendering_method"], meta["adapter_api"], meta.get("os_distribution") or meta["os"], meta["cpu"],
        meta["cpu_threads"], meta["window_px"][0], meta["window_px"][1], meta["engine"], meta["game_version"],
        str(meta["debug_build"]).lower(), soft))
    L.append("")
    L.append("Sample %ss per scenario after %ss warm-up, up to %d runs per configuration (interleaved). Rows show the "
             "best run (lowest average); `runs avg` lists every run's average so the run-to-run noise is visible. Times in ms."
             % (meta["sample_seconds"], meta["warmup_seconds"], args.repeats))
    for c in configs:
        if (c.startswith("no_") and not args.all_tables) or c not in picked:
            continue
        L.append("")
        L.append("### Configuration `%s`" % c)
        L.append("")
        L.append("| scenario | frames | avg | p50 | p90 | p95 | p99 | max | >16.7 ms | >20 ms | >33.4 ms | spikes | sim | proc | other | draw calls | nodes room/total | load | reload | runs avg |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for s in scen:
            if s not in picked[c]:
                continue
            p = picked[c][s]
            b = p["best"]
            L.append("| %s | %d | %.1f | %.1f | %.1f | %.1f | %.1f | %.1f | %d (%.0f%%) | %d (%.0f%%) | %d (%.0f%%) | %d | %.2f | %.2f | %.1f | %.0f | %d/%d | %.0f | %.0f | %s |" % (
                s, b["frames"], b["avg_ms"], b["p50_ms"], b["p90_ms"], b["p95_ms"], b["p99_ms"], b["max_ms"],
                b["over_16_7"], b["over_16_7_pct"], b["over_20"], b["over_20_pct"], b["over_33_4"], b["over_33_4_pct"], b["spikes"],
                b["sim_ms_per_frame"], b["process_ms_per_frame"], b["other_ms_per_frame"], b["draw_calls_avg"],
                b["nodes_room"], b["nodes_total"], b["load_total_ms"], b["reload_ms"], " / ".join("%.1f" % a for a in p["avgs"])))
    costs = [c for c in configs if c != "base" and c in picked]
    if "base" in picked and costs:
        L.append("")
        L.append("### Cost per system: average frame ms saved when it is switched off (best `base` run − best variant run)")
        L.append("")
        L.append("`~` marks a difference no larger than the gap between the two best runs of either configuration "
                 "(not distinguishable from noise). `n/a`: the room has no such system. In brackets: share of the base frame, "
                 "and the change in draw calls.")
        L.append("")
        L.append("| switched off | " + " | ".join(scen) + " |")
        L.append("|---|" + "---|" * len(scen))
        rows = []
        for c in costs:
            cells, score = [], 0.0
            for s in scen:
                if s not in picked["base"] or s not in picked[c]:
                    cells.append("n/a")
                    continue
                b, v = picked["base"][s], picked[c][s]
                d = b["best"]["avg_ms"] - v["best"]["avg_ms"]
                noise = max(b["gap"], v["gap"])
                dd = v["best"]["draw_calls_avg"] - b["best"]["draw_calls_avg"]
                score = max(score, d)
                cells.append("%s%.1f (%.0f%%, %+.0f dc)" % ("~" if abs(d) <= noise else "", d, 100.0 * d / b["best"]["avg_ms"], dd))
            rows.append((score, "| `%s` | %s |" % (c, " | ".join(cells))))
        for _, row in sorted(rows, key=lambda x: -x[0]):
            L.append(row)
    open(os.path.join(args.out, "summary.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--configs", default="base")
    ap.add_argument("--profile", action="store_true")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--seconds", type=float, default=8.0)
    ap.add_argument("--warmup", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=1988)
    ap.add_argument("--scenarios", default="", help="comma separated substrings of scenario names")
    ap.add_argument("--resolution", default="1280x720")
    ap.add_argument("--label", default="")
    ap.add_argument("--game", default=GAME, help="project directory to measure (default: this checkout's game/); "
                    "point it at a frozen copy to compare two builds or to keep editing while a run is in progress")
    ap.add_argument("--godot", default=shutil.which("godot") or "godot")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--force", action="store_true", help="re-run configurations that already have results")
    ap.add_argument("--summary-only", action="store_true")
    ap.add_argument("--all-tables", action="store_true", help="print the full frame-time table for no_<system> configurations too")
    args = ap.parse_args()
    configs = [c for c in args.configs.split(",") if c]
    if args.profile:
        configs = ["base"] + ["no_" + s for s in PROFILE_SYSTEMS] + ["postfx_off", "reduced", "reduced_postfx_off"]
    args.out = os.path.abspath(args.out)   # the harness runs with game/ as its working directory
    args.game = os.path.abspath(args.game)
    os.makedirs(args.out, exist_ok=True)
    if not args.summary_only:
        for rep in range(args.repeats):
            print("repeat %d/%d" % (rep + 1, args.repeats), flush=True)
            for c in configs:
                run_one(c, rep, args)
    summarise(args, configs)


if __name__ == "__main__":
    main()
