"""Google Sites HTML -> JSON list of blocks: {tag, id, runs:[{text,bold,italic,color,href}], align}."""
import sys, json, re
from html.parser import HTMLParser
BLOCK={'p','h1','h2','h3','h4','h5','h6','li','td','div'}
VOID={'img','br','hr','meta','link','input','col','area','base','embed','source','track','wbr'}
class P(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True); s.stack=[]; s.blocks=[]; s.cur=None; s.skip=0
    def flush(s):
        if s.cur and ''.join(r['text'] for r in s.cur['runs']).strip(): s.blocks.append(s.cur)
        s.cur=None
    def style(s):
        st={'bold':False,'italic':False,'color':None,'href':None}
        for tag,a in s.stack:
            sty=a.get('style') or ''
            m=re.search(r'(?:^|;)\s*color:\s*([^;]+)',sty)
            if m: st['color']=m.group(1).strip()
            m=re.search(r'font-weight:\s*(\w+)',sty)
            if m: st['bold']=m.group(1) in('bold','700','800','900')
            m=re.search(r'font-style:\s*(\w+)',sty)
            if m: st['italic']=m.group(1)=='italic'
            if tag in('b','strong'): st['bold']=True
            if tag in('i','em'): st['italic']=True
            if tag=='a': st['href']=a.get('href')
        return st
    def handle_starttag(s,t,attrs):
        a=dict(attrs)
        if t in('script','style','noscript','svg'): s.skip+=1; return
        if s.skip: return
        if t=='br':
            s.text('\n'); return
        if t=='img':
            if s.cur is None: s.flush()
            s.blocks.append({'tag':'img','src':a.get('src'),'runs':[]}); return
        if t in VOID: return
        if t in('p','h1','h2','h3','h4','h5','h6','li'):
            s.flush()
            sty=a.get('style') or ''
            m=re.search(r'text-align:\s*(\w+)',sty)
            s.cur={'tag':t,'id':a.get('id'),'align':m.group(1) if m else None,'runs':[]}
        s.stack.append((t,a))
    def handle_endtag(s,t):
        if t in('script','style','noscript','svg'):
            s.skip=max(0,s.skip-1); return
        if s.skip or t in VOID: return
        for i in range(len(s.stack)-1,-1,-1):
            if s.stack[i][0]==t:
                del s.stack[i:]; break
        if t in('p','h1','h2','h3','h4','h5','h6','li'): s.flush()
    def text(s,x):
        if s.cur is None: return
        st=s.style(); st['text']=x
        r=s.cur['runs']
        if r and all(r[-1][k]==st[k] for k in('bold','italic','color','href')): r[-1]['text']+=x
        else: r.append(st)
    def handle_data(s,d):
        if not s.skip: s.text(d)
p=P(); p.feed(open(sys.argv[1],encoding='utf-8').read()); p.flush()
json.dump(p.blocks,open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False,indent=0)
print(sys.argv[1],len(p.blocks))
