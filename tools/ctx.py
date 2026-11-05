import json,re
d=json.load(open('docs/data/services.json',encoding='utf-8'))
for slug,items in d.items():
    for it in items:
        if 'r' not in it: continue
        t=''.join(r[0] for r in it['r'])
        for m in re.finditer(r"(\.{2,}|…)",t):
            print(slug[:10],it.get('i'),('H' if it.get('w')=='false' else ''),'«'+t[max(0,m.start()-62):m.end()+28]+'»')
