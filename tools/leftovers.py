import json,re,glob,collections
N=lambda x:re.sub(r'\s+',' ',x.replace('­','').replace(' ',' ').translate(str.maketrans('şţŞŢ','șțȘȚ')))
pat=re.compile(r"([^.…:;!?()]{2,90}?)\s*(\.{2,}|…)")
found=collections.OrderedDict()
def scan(where,items):
    for it in items:
        if 'r' not in it or it.get('w')=='false': continue
        for run in it['r']:
            for m in pat.finditer(run[0]):
                k=m.group(1).strip(' ,')
                if k: found.setdefault(k,[]).append((where,'R' if 'r' in run[1] else 'b'))
d=json.load(open('docs/data/services.json',encoding='utf-8'))
for s,i in d.items(): scan(s,i)
for f in ['psaltire','canon-treime']+[f'canon-md-{g}' for g in range(1,9)]:
    x=json.load(open(f'docs/data/{f}.json',encoding='utf-8'))
    for k,v in x.items():
        if isinstance(v,list): scan(f,v)
        else:
            for e,l in v.items(): scan(f,l)
h=json.load(open('docs/data/hymns.json',encoding='utf-8'))
s=json.load(open('docs/data/sinaxar.json',encoding='utf-8'))
def walk(o,w):
    if isinstance(o,str):
        for m in pat.finditer(o): found.setdefault(m.group(1).strip(' ,'),[]).append((w,'h'))
    elif isinstance(o,dict):
        for v in o.values(): walk(v,w)
    elif isinstance(o,list):
        for v in o: walk(v,w)
walk(h,"hymns"); walk({k:{'t':v['t'],'c':v['c']} for k,v in s.items()},'sinaxar')
# search sources
corp=[]
for f in glob.glob('source/blocks/*.json'):
    n=f.split('/')[-1][:-5]
    if n in('calendar','octoih') or n.startswith('minei'): continue
    for i,x in enumerate(json.load(open(f,encoding='utf-8'))):
        t=N(''.join(r['text'] for r in x.get('runs',[]))).strip()
        if t: corp.append((n,i,t))
print(len(found),sum(len(v) for v in found.values()))
rows=[]
for k,v in sorted(found.items(),key=lambda kv:-len(kv[1])):
    cand=None
    kk=re.escape(N(k)); rx=re.compile(kk+r"(?!\s*(?:\.{2,}|…))\s*[^\s]",re.I)
    for n,i,t in corp:
        m=rx.search(t)
        if m and len(t)-m.start()>len(k)+15:
            cand=(n,i,m.start()==0 or t[:m.start()].strip()=='' ,t[m.start():m.start()+70]);
            if cand[2]: break
    rows.append((len(v),k,sorted({w for w,_ in v})[:3],sorted({c for _,c in v}),cand))
for r in rows: print(r[0],'|',r[1][:60],'|',','.join(r[2])[:34],''.join(r[3]),'|',(f"{r[4][0]}:{r[4][1]}{'^' if r[4][2] else ''} {r[4][3][:50]}" if r[4] else 'NONE'))
