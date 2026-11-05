import json,re,collections,unicodedata
d=json.load(open('docs/data/services.json',encoding='utf-8'))
C=collections.Counter(); ex={}
# phrase = up to 7 words ending in an ellipsis, not crossing sentence ends
pat=re.compile(r"([A-ZĂÂÎȘȚa-zăâîșț][^.…:;!?()]{0,70}?)\s*(?:\.{2,}|…)")
for slug,items in d.items():
    for it in items:
        if 'r' not in it: continue
        for run in it['r']:
            if 'r' in run[1]: continue   # rubric text is not a prayer
            for m in pat.finditer(run[0]):
                k=re.sub(r'\s+',' ',m.group(1)).strip(' ,')
                C[k]+=1; ex.setdefault(k,slug)
print(len(C),sum(C.values()))
for k,v in C.most_common(130): print(v,'|',k,'|',ex[k])
