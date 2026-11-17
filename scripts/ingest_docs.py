"""Ingest：把 Claude Docs《臺灣常用藥物講義》12 個分頁的 XML 讀取結果轉成 raw/*.md。

用法：python3 scripts/ingest_docs.py <存放 read 結果的資料夾> [<對話紀錄 .jsonl>]
raw/ 一經產生即視為不可修改的原始資料；要更新請重新 ingest，不要手改。
"""
import json, re, sys, glob, os
import xml.etree.ElementTree as ET

TR = (sys.argv[1].rstrip('/') + '/') if len(sys.argv) > 1 else './tool-results/'
JSONL = sys.argv[2] if len(sys.argv) > 2 else None
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'raw') + '/'

def xml_from_text(t):
    i = t.find('{"verdict"')
    if i < 0: return None
    dec = json.JSONDecoder(strict=False)
    try: j, _ = dec.raw_decode(t[i:])
    except Exception: return None
    return j['data']['xml'] if isinstance(j.get('data'), dict) and j['data'].get('xml') and j['data'].get('complete') else None

xmls = {}
for f in glob.glob(TR + 'mcp-Claude_Docs-read-*.txt'):
    for x in json.load(open(f)):
        xm = xml_from_text(x['text'])
        if xm: xmls[re.search(r"<doc node='([^']+)'", xm).group(1)] = xm
# inline results from the transcript
for line in (open(JSONL, encoding='utf-8') if JSONL else []):
    if "<doc node='" not in line: continue
    try: rec = json.loads(line)
    except: continue
    def walk(o):
        if isinstance(o, str):
            if '<doc node=' in o and '{"verdict"' in o:
                xm = xml_from_text(o)
                if xm:
                    n = re.search(r"<doc node='([^']+)'", xm).group(1)
                    if n not in xmls: xmls[n] = xm
        elif isinstance(o, dict):
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(rec)

ORDER = [('01','autonomic','ea47555d-20af'),('02','cardiovascular','9da3804c-05c2'),('03','autacoids','687d33f2-d4b4'),
 ('04','cns','c5629e33-b085'),('05','blood-inflammation','6df16076-a954'),('06','gastrointestinal','a037b39f-c2b7'),
 ('07','respiratory','179836a8-fe45'),('08','urinary','7ea1f0b5-c06b'),('09','endocrine','29b89983-0396'),
 ('10','immunology','34ee92e6-baa2'),('11','antibacterial','cb85111c-9038'),('12','antimicrobial-other','dd617d68-71e9')]

def inline(el):
    out = ''
    if el.text and el.tag not in ('doc',): pass
    for c in el:
        if c.tag == 'text':
            s = ''.join(c.itertext())
            if c.find('bold') is not None: s = '**' + s + '**'
            if c.find('italic') is not None: s = '*' + s + '*'
            out += s
        elif c.tag == 'date': out += c.get('value', '')
        elif c.tag == 'mention': out += '@' + c.get('name', '')
        elif c.tag == 'link': out += '[' + ''.join(c.itertext()) + '](' + c.get('href', '') + ')'
        else: out += ''.join(c.itertext())
    return out.replace('\n', ' ').strip()

def cell_text(cell):
    parts = [inline(p) for p in cell if p.tag == 'paragraph']
    return '<br>'.join(x for x in parts if x).replace('|', '／') or ' '

def block(el, depth=0):
    t = el.tag
    if t == 'paragraph':
        h = el.get('heading'); s = inline(el)
        if not s: return ''
        return ('#' * int(h) + ' ' + s) if h else s
    if t == 'table':
        rows = [r for r in el if r.tag == 'row']
        if not rows: return ''
        cells = [[cell_text(c) for c in r if c.tag == 'cell'] for r in rows]
        n = max(len(r) for r in cells)
        cells = [r + [' '] * (n - len(r)) for r in cells]
        lines = ['| ' + ' | '.join(cells[0]) + ' |', '|' + ' --- |' * n]
        lines += ['| ' + ' | '.join(r) + ' |' for r in cells[1:]]
        return '\n'.join(lines)
    if t == 'list':
        ordered = el.get('kind') == 'ordered'; out = []
        for i, li in enumerate([x for x in el if x.tag == 'listItem'], 1):
            sub = [block(x, depth + 1) for x in li]
            first = sub[0] if sub else ''
            rest = [s for s in sub[1:] if s]
            mark = f'{i}.' if ordered else '-'
            out.append('   ' * depth + f'{mark} {first}')
            for s in rest: out.append('\n'.join('   ' * (depth + 1) + l for l in s.split('\n')))
        return '\n'.join(out)
    if t == 'embed':
        return f"> 〔原講義此處有圖：{el.get('caption','圖表')}〕"
    if t in ('callout', 'quote', 'blockquote'):
        inner = '\n\n'.join(b for b in (block(x) for x in el) if b)
        return '\n'.join('> ' + l for l in inner.split('\n'))
    inner = [block(x, depth) for x in el]
    return '\n\n'.join(b for b in inner if b)

missing = []
for cid, slug, node in ORDER:
    if node not in xmls: missing.append(node); continue
    root = ET.fromstring(xmls[node])
    md = '\n\n'.join(b for b in (block(x) for x in root) if b) + '\n'
    src = (f'---\nsource: 臺灣常用藥物講義（Claude Docs artifact，作者 Lan）\nurl: https://claude.ai/artifact/SDKyRL15WenarMrF7J1hsW\n'
           f'tab_node: {node}\nretrieved: 2026-11-17\n---\n\n')
    open(f'{OUT}{cid}-{slug}.md', 'w', encoding='utf-8').write(src + md)
print('missing:', missing)
for f in sorted(os.listdir(OUT)):
    p = OUT + f; s = open(p, encoding='utf-8').read()
    print(f, len(s), 'tables', s.count('\n| ---') + s.count('\n|---'), 'h2', len(re.findall(r'^## ', s, re.M)))
