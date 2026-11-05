import json,sys,re
f,a,c=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]); w=int(sys.argv[4]) if len(sys.argv)>4 else 400
b=json.load(open(f'blocks/{f}.json',encoding='utf-8'))
for i in range(a,min(c,len(b))):
    x=b[i]
    if x['tag']=='img': print(i,'[IMG]'); continue
    o=''
    for r in x['runs']:
        t=r['text'].replace('\n',' / ')
        if r['color'] in('#ff0000','#980000','#660000'): t='{R:'+t+'}'
        if r.get('href'):
            m=re.search(r'#(h\.\w+)',r['href']); t='['+t+'->'+(r['href'].split('/')[-1][:18]+'#'+m.group(1)[:10] if m else '?')+']'
        o+=t
    print(i,x['tag'],x.get('align') or '',o[:w] + ('…'+str(len(o)) if len(o)>w else ''))
