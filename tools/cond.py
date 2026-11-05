import json,sys,re
f,a,c,w=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4])
b=json.load(open(f'blocks/{f}.json',encoding='utf-8'))
RED=('#ff0000','#980000','#660000')
K=re.compile(r'(?i)dac[ăa] |iar |postul|post |duminic|s[âa]mb[ăa]t|luni|mar[țţt]i|miercuri|joi|vineri|praznic|polieleu|doxolog|priveghere|penticostar|triod|s[ăa]pt[ăa]m|paș|paş|aliluia|lumin[ăa]t')
for i in range(a,c):
    x=b[i]
    if x['tag']=='img': continue
    o='';red=''
    for r in x['runs']:
        t=r['text'].replace('\n','/')
        if r.get('href'): t='['+t.strip()+']';red+=t
        elif r['color'] in RED and len(t.strip())>1: red+=t; t='{'+t+'}'
        o+=t
    o=re.sub(r'\}\{','',re.sub(r'\s+',' ',o)).strip()
    if x['tag']=='h2': print(f'\n## {i} {o[:80]}'); continue
    if K.search(red): print(i,o[:w]+('…' if len(o)>w else ''))
