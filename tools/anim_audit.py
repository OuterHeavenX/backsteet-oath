#!/usr/bin/env python3
"""Checks that attack animations agree with real hit timing.

For every attack in game/data/attacks.json and every character sheet that can perform it, this reproduces the
engine's frame mapping (Actor._attack_frame): anticipation frames are spread over the start-up ticks, the contact
frame is held for the active ticks, follow-through frames are spread over the recovery ticks. It reports:
  - NO_WINDUP      a telegraphed or slow (>= 10 tick) start-up with no anticipation frame at all
  - POP            an anticipation or follow-through frame shown for less than 2 ticks (33 ms)
  - FROZEN         12+ recovery ticks with no follow-through frame (contact pose held)
  - MISSING_ANIM   the sheet has no such animation (the engine falls back to idle)
Usage: python3 tools/anim_audit.py [--md out.md]
"""
import json, os, sys, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIASES = {}
def sheets():
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'game/assets/sprites/chars/*.json'))):
        d = json.load(open(f))
        out[os.path.basename(f)[:-5]] = d.get('anims', {})
    return out
def users(attack_id, group, sh, enemies):
    """Which sheets perform this attack."""
    if group in ('player', 'weapon'):
        return ['nico']
    names = []
    arche = enemies['archetypes']
    for a, ad in arche.items():
        ids = [x[0] for x in ad.get('attacks', [])]
        if attack_id in ids or (attack_id == 'e_counter' and ad.get('counter')) or (attack_id == 'e_jump_kick' and a == 'flanker'):
            names += [s for s in sh if s.endswith('_' + a)]
    boss_sets = {
        'duke': ['duke_chain', 'duke_spin', 'e_charge', 'e_cross'], 'rhea': ['pike_pole', 'pike_sweep', 'e_kick', 'e_charge'],
        'lou': ['e_throw', 'lou_lob', 'e_kick', 'lou_hop'], 'otto': ['otto_haymaker', 'otto_slam', 'otto_charge', 'e_grab'],
        'jett': ['jett_flip', 'jett_dash', 'jett_combo'], 'sabine': ['sabine_baton', 'sabine_bash', 'e_hook', 'e_kick', 'sabine_counter'],
        'kowal': ['kowal_spade', 'kowal_sweep', 'kowal_snuff', 'pike_pole', 'pike_sweep', 'duke_spin', 'e_charge', 'e_cross'],
        'mae': ['rook_jab', 'rook_combo', 'rook_uppercut', 'jett_dash', 'e_kick', 'e_counter'],
        'rook': ['rook_jab', 'rook_combo', 'rook_uppercut', 'rook_dash', 'rook_counter'],
        'rook_p2': ['rook_pipe', 'rook_pound', 'rook_dash', 'rook_uppercut', 'rook_combo'],
    }
    for b, ids in boss_sets.items():
        if attack_id in ids and b in sh:
            names.append(b)
    return sorted(set(names))
def audit():
    atk = json.load(open(os.path.join(ROOT, 'game/data/attacks.json')))
    enemies = json.load(open(os.path.join(ROOT, 'game/data/enemies.json')))
    sh = sheets()
    rows, issues = [], []
    for group in ('player', 'weapon', 'enemy'):
        for aid, d in atk[group].items():
            if 'anim' not in d:
                continue
            us = users(aid, group, sh, enemies)
            seen = set()
            for u in us:
                anims = sh[u]
                ad = anims.get(d['anim'])
                if ad is None:
                    issues.append((aid, u, 'MISSING_ANIM', d['anim']))
                    continue
                n = len(ad['frames']); c = min(max(int(ad.get('contact', 0)), 0), n - 1)
                s = int(d.get('startup', 4)); a = int(d.get('active', 3)); r = max(1, int(d.get('recovery', 8)))
                rem = n - 1 - c
                key = (n, c)
                if key in seen:
                    continue
                seen.add(key)
                used = min(max(s // 2, 1), c) if c > 0 else 0      # engine: fast moves keep only the last wind-up pose
                wind = s / used if used > 0 else 0.0
                follow = r / rem if rem > 0 else 0.0
                flags = []
                if c == 0 and (d.get('telegraph') or s >= 10) and not d.get('air'):
                    # telegraphed attacks also get a procedural lean (Actor._attack_lean), so a held pose still moves
                    flags.append('HELD_POSE(lean only)' if d.get('telegraph') else 'NO_WINDUP')
                if c > 0 and s > 0 and wind < 2.0:
                    flags.append('POP(windup)')
                if rem > 0 and follow < 2.0:
                    flags.append('POP(follow)')
                if rem == 0 and r >= 12 and not d.get('air'):
                    flags.append('FROZEN')
                rows.append((group, aid, d['anim'], u, n, c, s, a, r, round(wind, 1), round(follow, 1), ' '.join(flags)))
                for fl in flags:
                    issues.append((aid, u, fl, d['anim']))
    return rows, issues
def main():
    rows, issues = audit()
    hdr = ('group', 'attack', 'anim', 'sheet', 'frames', 'contact', 'startup', 'active', 'recovery', 'ticks/windup frame', 'ticks/follow frame', 'flags')
    lines = ['| ' + ' | '.join(hdr) + ' |', '|' + '---|' * len(hdr)]
    for r in rows:
        lines.append('| ' + ' | '.join(str(x) for x in r) + ' |')
    text = '\n'.join(lines)
    if '--md' in sys.argv:
        open(sys.argv[sys.argv.index('--md') + 1], 'w').write(
            '# Attack animation vs. hit timing\n\nGenerated by `tools/anim_audit.py`. Ticks are 1/60 s.\n\n' + text + '\n\n' +
            ('## Flags\n\n' + '\n'.join('- `%s` on `%s`: %s (%s)' % (a, u, f, an) for a, u, f, an in issues) if issues else 'No flags.') + '\n')
    for r in rows:
        if r[-1]:
            print('%-8s %-16s %-11s %-14s n=%d c=%d s=%d a=%d r=%d  %s' % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[-1]))
    print('%d attack/sheet combinations checked, %d flagged' % (len(rows), len([r for r in rows if r[-1]])))
if __name__ == '__main__':
    main()
