import json,sys,re
f,a,c=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]); w=int(sys.argv[4])
b=json.load(open(f'blocks/{f}.json',encoding='utf-8'))
RED=('#ff0000','#980000','#660000')
for i in range(a,c):
    x=b[i]
    if x['tag']=='img': print(i,'IMG'); continue
    o=''; red=0; L=[]
    for r in x['runs']:
        t=r['text'].replace('\n','/')
        if r.get('href'): L.append(t.strip()); t='['+t.strip()+']'
        elif r['color'] in RED and len(t.strip())>1: t='{'+t+'}'; red+=len(t)
        o+=t
    o=re.sub(r'\}\{','',re.sub(r'\s+',' ',o)).strip()
    if x['tag']=='h2' or L or red>8:
        print(i,o[:w]+('…' if len(o)>w else ''))
    else:
        print(i,'·',o[:38])
