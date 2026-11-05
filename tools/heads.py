import json,sys
b=json.load(open(f'blocks/{sys.argv[1]}.json',encoding='utf-8'))
print(sys.argv[1],len(b),sum(len(r['text']) for x in b for r in x['runs']))
for i,x in enumerate(b):
    if x['tag'] in('h1','h2','h3'): print(i,x['tag'],''.join(r['text'] for r in x['runs'])[:80].replace('\n',' / '))
