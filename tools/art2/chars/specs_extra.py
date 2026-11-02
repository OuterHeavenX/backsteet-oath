"""v2-only character specs (content expansion, docs/CONTENT_EXPANSION.md sections 2 and 6).

Same schema as the v1 tables in tools/art/gen_characters.py (built with its CH()/J() helpers), plus v2 keys:
  shirt patterns 'hivis' / 'benny', hat kinds 'lamphat' / 'bucket',
  extras 'dustmask', 'lanyard', 'paint', 'goggles', 'spraycan', 'vest_over:<colour>'.
"""
from draw import V1

CH, J = V1.CH, V1.J
ORANGE, NAVY, DUST = '#e8742a', '#2b3a55', '#b8a27a'
OLIVE = '#6e6a3c'

MOLES = [
    CH('moles_brawler', skin='tan', hair='short', hcol='black', hat=('lamphat', 'yellow'), face='tough',
       shirt=NAVY, sleeves='long', overalls=NAVY, pants=NAVY, jacket=J(ORANGE, kind='safety', sleeves='none'),
       gloves=DUST, shoes='black', sstyle='boot', extras=('dustmask',), fhair='stubble', fhcol='black'),
    CH('moles_flanker', body='slim', skin='light', hair='short', hcol='auburn', hat=('lamphat', 'white'),
       face='cocky', shirt=NAVY, sleeves='long', jacket=J(NAVY, kind='hoodie', open=False, collar='hood'),
       pants=NAVY, gloves=DUST, shoes='black', sstyle='boot', extras=('vest_over:' + ORANGE, 'dustmask')),
    CH('moles_blocker', skin='medium', hair='short', hcol='black', hat=('lamphat', 'yellow'), face='tough',
       shirt=NAVY, sleeves='rolled', overalls=NAVY, pants=NAVY, jacket=J(ORANGE, kind='safety', sleeves='none'),
       guards=DUST, gloves=DUST, shoes='black', sstyle='boot', extras=('dustmask',)),
    CH('moles_heavy', body='heavy', skin='light', hair='short', hcol='brown', hat=('lamphat', 'orange'),
       fhair='beard', fhcol='brown', face='tough', shirt=DUST, sleeves='rolled', overalls=NAVY, pants=NAVY,
       gloves=DUST, shoes='black', sstyle='boot', extras=('vest_over:' + ORANGE,)),
    CH('moles_weapon', bulk=True, skin='deep', hair='short', hcol='black', hat=('lamphat', 'white'), marks=('scar',),
       fhair='stubble', fhcol='black', face='mean', shirt=NAVY, sleeves='long', overalls=NAVY, pants=NAVY,
       jacket=J(ORANGE, kind='safety', sleeves='none'), gloves='black', shoes='black', sstyle='boot',
       extras=('dustmask',)),
    CH('moles_thrower', body='slim', skin='tan', hair='short', hcol='darkbrown', hat=('lamphat', 'yellow'),
       face='cocky', shirt=NAVY, sleeves='long', jacket=J(NAVY, kind='hoodie', open=False, collar='hood'),
       pants=NAVY, gloves=DUST, shoes='black', sstyle='boot', extras=('vest_over:' + ORANGE, 'bag:' + DUST)),
]

STORY2 = [
    CH('kowal', body='tall', skin='light', hair='braid', hcol='gray', hat=('lamphat', 'yellow'), face='stern',
       shirt='hivis', sleeves='long', jacket=J(OLIVE, kind='coat', length='long', collar='high'), pants='charcoal',
       shoes='black', sstyle='boot', gloves=DUST, lashes=True, extras=('goggles',), boss_scale=1.03),
    CH('mae', bulk=True, skin='deep', hair='ponytail', hcol='black', face='determined', shirt='benny',
       sleeves='none', pants=NAVY, pstyle='track', shoes='white', sole='lightgray', gloves='white', wrist='white',
       lashes=True),
    CH('ines', skin='medium', hair='bob', hcol='darkbrown', glasses='round', face='kind', shirt='#5fa8a0',
       sleeves='short', jacket=J('#8a6a9a', kind='cardigan'), pants='#5fa8a0', shoes='white', sole='lightgray',
       lashes=True, civilian=True, extras=('lanyard',)),
    CH('otis', body='elder', skin='deep', hair='short', hcol='white', hat=('police', 'navy'), fhair='mustache',
       fhcol='white', face='kind', shirt='white', sleeves='long', jacket=J('brown', kind='cardigan'), pants='charcoal',
       shoes='black', sstyle='dress', civilian=True),
    CH('kiki', body='slim', skin='tan', hair='bob', hcol='purple', hat=('bucket', 'mustard'), face='cheerful',
       shirt='white', sleeves='short', overalls='denim', pants='denim', shoes='checker', lashes=True, civilian=True,
       extras=('paint', 'spraycan'), boss_scale=0.95),
    CH('sal', body='heavy', skin='light', hair='short', hcol='gray', hat=('flatcap', 'gray'), face='neutral',
       shirt='white', sleeves='rolled', apron='rubbergreen', pants='charcoal', shoes='black', sstyle='rubber',
       fhair='stubble', fhcol='gray', civilian=True),
]

EXTRA = MOLES + STORY2
EXTRA_BY_ID = {c['id']: c for c in EXTRA}
EXTRA_GANGS = {'moles': 'The Moles'}
EXTRA_GANG_PORTRAIT = {'moles': 'moles_weapon'}
EXTRA_PORTRAITS = ['kowal', 'mae', 'ines', 'otis', 'kiki', 'sal', 'moles']
