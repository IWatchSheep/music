"""Independent synthetic held-out oracle. Run from project root with PYTHONPATH=. python this_file.py."""
from fractions import Fraction as F
from types import SimpleNamespace as N
from itertools import combinations
from collections import defaultdict
from music_model.recurrence_discovery import discover_sound_groups
M=('exact','transposition','rhythm','contour','interval_only','rhythm_proportional')
def phrase(row,p,d,q=None,t=0,voice=None,prefix=''):
    q=q if q is not None else d[:-1]; out=[]
    for i,(x,y) in enumerate(zip(p,d)):
        out.append(N(start_ms=F(t),end_ms=F(t)+F(y),pitch=x,event_id=f'{row}:{prefix}:{i}',voice=voice))
        if i<len(q): t+=q[i]
    return out
# Hand constructed labels, before invoking the engine. Each expectation names the two starts and relation.
a=[59,64,64,61,67]; d=[F(7,3),F(5,2),F(4,3),F(9,2),F(2)]; q=[3,4,2,5]
def two(p2,d2,q2): return {'r':phrase('r',a,d,q,prefix='a')+phrase('r',p2,d2,q2,t=40,prefix='b')}
cases=[
 ('fractional_exact',two(a,d,q), [('exact',5,'r',0,'r',5)]),
 ('negative_transpose',two([p-11 for p in a],d,q), [('transposition',5,'r',0,'r',5)]),
 ('rhythm_only',two([72,69,71,65,63],d,q), [('rhythm',5,'r',0,'r',5)]),
 ('contour_only',two([70,71,71,63,64],[2]*5,[3]*4), [('contour',5,'r',0,'r',5)]),
 ('interval_only',two([p+3 for p in a],[2]*5,[3]*4), [('interval_only',5,'r',0,'r',5)]),
 ('scaled_rhythm',two([72,69,71,65,63],[x*F(7,4) for x in d],[F(x)*F(7,4) for x in q]), [('rhythm_proportional',5,'r',0,'r',5)]),
 ('near_pitch',two(a[:-1]+[F(67)+F(1,10**20)],d,q), [('rhythm',5,'r',0,'r',5)]),
 ('near_timing',two(a,d[:-1]+[d[-1]+F(1,10**20)],q), [('interval_only',5,'r',0,'r',5)]),
 ('cross_row',{'z':phrase('z',a,d,q),'a':phrase('a',[p+17 for p in a],d,q,t=99)}, [('transposition',5,'a',0,'z',0)]),
 ('unpitched',two([59,64,None,61,67],d,q), [('rhythm',5,'r',0,'r',5)]),
 ('overlap_only',{'r':phrase('r',[60]*5,[1]*5)}, []),
 ('periodic_overlap',{'r':phrase('r',[60]*9,[1]*9)}, [('exact',4,'r',0,'r',4)]),
 ('negative',{'r':phrase('r',[60,72,61,65,63,78,59],[1,2,3,4,5,6,7])}, []),
 ('empty',{},[]),('short',{'r':phrase('r',[60,62],[1,1])},[]),
 ('explicit_voices',{'r':phrase('r',a,d,q,voice='upper',prefix='a')+phrase('r',a,d,q,voice='lower',prefix='b')},[]),
 ('ambiguous_chord',{'r':phrase('r',a,d,q,prefix='a')+phrase('r',a,d,q,prefix='b')},[]),
]
def equal(m,x,y):
    # Compare individual values directly; no implementation signature helpers.
    if m not in ('rhythm','rhythm_proportional') and any(n.pitch is None for n in x+y): return False
    ratio=(y[0].end_ms-y[0].start_ms)/(x[0].end_ms-x[0].start_ms) if m=='rhythm_proportional' else F(1)
    shift=y[0].pitch-x[0].pitch if m in ('transposition','interval_only') else 0
    for i,(u,v) in enumerate(zip(x,y)):
        if m in ('exact','transposition','rhythm','rhythm_proportional'):
            if (u.end_ms-u.start_ms)*ratio!=v.end_ms-v.start_ms or (u.start_ms-x[0].start_ms)*ratio!=v.start_ms-y[0].start_ms: return False
        if m in ('exact','transposition','interval_only') and v.pitch-u.pitch!=shift: return False
        if m=='contour' and i:
            a=u.pitch-x[i-1].pitch; b=v.pitch-y[i-1].pitch
            if (a>0)-(a<0)!=(b>0)-(b<0): return False
    return True
checks=0; failures=[]
def check(ok,label):
    global checks
    checks+=1
    if not ok: failures.append(label)
for name,rows,intended in cases:
    streams=defaultdict(list)
    for r,notes in rows.items():
        for note in notes: streams[(r,note.voice)].append(note)
    for s in streams.values(): s.sort(key=lambda n:n.start_ms)
    eligible={k:s for k,s in streams.items() if all(s[i].start_ms>=max(x.end_ms for x in s[:i]) for i in range(1,len(s)))}
    result=discover_sound_groups(rows,methods=M,max_length=5)
    for m in M:
        for n in range(3,6):
            windows=[(k,i,s[i:i+n]) for k,s in eligible.items() for i in range(len(s)-n+1)]
            expected=set()
            for (k,i,x),(l,j,y) in combinations(windows,2):
                if k==l and abs(i-j)<n: continue
                if equal(m,x,y): expected.add(frozenset(((k,i),(l,j))))
            actual=set()
            for f in result.all_families:
                if f.method!=m or f.length!=n: continue
                for u,v in combinations(f.occurrences,2):
                    k=(u.row_id,u.voice_id); l=(v.row_id,v.voice_id)
                    if k==l and abs(u.start_index-v.start_index)<n: continue
                    actual.add(frozenset(((k,u.start_index),(l,v.start_index))))
            check(expected==actual,f'{name} {m} {n}: expected {len(expected)}, got {len(actual)}')
    for m,n,r,i,s,j in intended:
        check(any(f.method==m and f.length==n and {(r,i),(s,j)}<={(o.row_id,o.start_index) for o in f.occurrences} for f in result.all_families),f'{name} intended {m}')
    check(result==discover_sound_groups({r:list(reversed(s)) for r,s in reversed(list(rows.items()))},methods=M,max_length=5),name+' reverse')
    for f in result.all_families:
        for o in f.occurrences:
            check(all(e.source is streams[(o.row_id,o.voice_id)][e.chronological_index] for e in o.events),name+' source refs')
    print(name, 'families',len(result.all_families))
print('checks',checks,'failures',len(failures));print('\n'.join(failures));raise SystemExit(bool(failures))
