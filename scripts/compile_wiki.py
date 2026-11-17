#!/usr/bin/env python3
"""Compile：由 raw/ 產生 Wiki 的「類別頁」「彙整頁」與 index.md。

- class-NN-K.md   ：raw 第 NN 篇的第 K 個 H2 章節（含表格者），原文照搬並加上來源與相關連結
- agg-drug-index  ：跨 12 篇的藥名索引（藥名 → 出現在哪些類別頁）
- agg-suffix      ：12 篇「字尾辨識法」合併
- agg-scenarios   ：12 篇「重點總結／臨床情境」表格合併
- index.md        ：所有頁面目錄（概念頁讀自 wiki/concept-*.md 的 frontmatter）

概念頁（concept-*.md）由 AI 撰寫，本腳本不會覆寫。
用法：python3 scripts/compile_wiki.py
"""
import os, re, glob
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RAW, WIKI = os.path.join(ROOT, 'raw'), os.path.join(ROOT, 'wiki')
CN = '一二三四五六七八九十'
META = re.compile(r'速覽|字尾|重點總結|總論|臨床情境')
NOT_DRUG = {'Class', 'Gram', 'Torsades', 'Hofmann', 'FDA', 'Gq', 'Gi', 'Gs', 'Line', 'Track',
            'Nitrostat', 'Plus', 'Type', 'Stage', 'Child', 'Pugh', 'Score', 'Gate', 'Na', 'Cl'}


def cn_index(n):
    return CN[n - 1] if n <= 10 else '十' + CN[n - 11]


def parse_raw(path):
    text = open(path, encoding='utf-8').read()
    body = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.S)
    h1 = re.search(r'^# (.+)$', body, re.M).group(1).strip()
    parts = re.split(r'^## (.+)$', body, flags=re.M)
    secs = [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts), 2)]
    return h1, secs


def tables(md):
    """回傳 [(header, rows)]"""
    out, lines, i = [], md.split('\n'), 0
    while i < len(lines):
        if lines[i].startswith('|') and i + 1 < len(lines) and re.match(r'^\|\s*-{3}', lines[i + 1]):
            row = lambda l: [c.strip() for c in l.strip().strip('|').split('|')]
            head, rows, j = row(lines[i]), [], i + 2
            while j < len(lines) and lines[j].startswith('|'):
                rows.append(row(lines[j])); j += 1
            out.append((head, rows)); i = j
        else:
            i += 1
    return out


def drug_names(cell):
    cell = re.sub(r'\*\*|<br>', ' ', cell)
    names = re.findall(r'(?<![A-Za-z])[A-Z][a-z][a-zA-Z]{3,}(?:[ -][a-z]{4,})?(?![A-Za-z])', cell)
    return [n for n in names if n.split()[0] not in NOT_DRUG]


def fm(d):
    def val(v):
        return '[' + ', '.join(v) + ']' if isinstance(v, list) else v
    return '---\n' + '\n'.join(f'{k}: {val(v)}' for k, v in d.items()) + '\n---\n\n'


def main():
    for f in glob.glob(os.path.join(WIKI, 'class-*.md')) + glob.glob(os.path.join(WIKI, 'agg-*.md')):
        os.remove(f)

    chapters, classes = [], []
    drug_pages = defaultdict(list)
    brands = set()
    suffix_rows, scen_rows = [], []

    for path in sorted(glob.glob(os.path.join(RAW, '*.md'))):
        stem = os.path.basename(path)[:-3]
        nn = stem[:2]
        h1, secs = parse_raw(path)
        short = re.sub(r'^臺灣常用|藥物講義|講義', '', h1).strip() or h1
        chapters.append((nn, stem, h1, short))
        for k, (h2, body) in enumerate(secs, 1):
            m = re.match(r'^([一二三四五六七八九十]+)、(.+)$', h2)
            num, title = (m.group(1), m.group(2)) if m else (cn_index(k), h2)
            src = f'{stem}#{num}'
            tbls = tables(body)
            if re.search(r'字尾', h2):
                for head, rows in tbls:
                    for r in rows:
                        suffix_rows.append((r + ['', '', ''])[:3] + [src])
                continue
            if re.search(r'重點總結|臨床情境', h2):
                for head, rows in tbls:
                    if len(head) >= 2:
                        for r in rows:
                            scen_rows.append([r[0], ' ／ '.join(r[1:]), src, short])
                continue
            if META.search(h2) or not tbls:
                continue
            pid = f'class-{nn}-{k}'
            drugs = []
            for head, rows in tbls:
                cols = [i for i, h in enumerate(head) if re.search(r'學名|藥物|代表藥|逆轉劑|藥$', h)] or [0]
                bcols = [i for i, h in enumerate(head) if '商品名' in h]
                for r in rows:
                    for c in cols:
                        if c < len(r):
                            drugs += drug_names(r[c])
                    for c in bcols:
                        if c < len(r):
                            brands.update(drug_names(r[c]))
            classes.append(dict(id=pid, title=title, chapter=short, src=src, body=body, drugs=drugs, nn=nn))

    # 只出現在「商品名」欄的字（如 Aldactone、Bridion）不算藥名
    generics = set()
    for c in classes:
        for head, rows in tables(c['body']):
            if head and head[0] == '學名':
                for r in rows:
                    generics.update(drug_names(r[0]))
    for c in classes:
        c['drugs'] = [d for d in dict.fromkeys(c['drugs']) if d not in brands or d in generics]
        for d in c['drugs']:
            drug_pages[d].append(c['id'])
    by_id = {c['id']: c for c in classes}

    for c in classes:
        overlap = defaultdict(int)
        for d in c['drugs']:
            for p in drug_pages[d]:
                if p != c['id']:
                    overlap[p] += 1
        rel = [p for p, _ in sorted(overlap.items(), key=lambda x: (-x[1], x[0]))[:6]]
        body = re.sub(r'^### ', '## ', c['body'], flags=re.M)
        md = fm(dict(id=c['id'], title=c['title'], type='class', chapter=c['chapter'],
                     sources=[c['src']], related=rel))
        md += f"# {c['title']}\n\n"
        md += f"> 出自〈{c['chapter']}〉講義第{c['src'].split('#')[1]}節〔{c['src']}〕。本頁由 `compile_wiki.py` 自動產生，內容與原講義相同。\n\n"
        md += body + '\n\n'
        if c['drugs']:
            md += '## 本頁藥物\n\n' + '、'.join(c['drugs']) + '\n\n'
        if rel:
            md += '## 相關類別（共用藥物）\n\n' + '\n'.join(
                f"- [[{p}|{by_id[p]['title']}]]（{by_id[p]['chapter']}）" for p in rel) + '\n'
        open(os.path.join(WIKI, c['id'] + '.md'), 'w', encoding='utf-8').write(md)

    # 彙整頁：藥名索引
    md = fm(dict(id='agg-drug-index', title='跨篇藥名索引', type='aggregate',
                 sources=[s for _, s, _, _ in chapters], related=['agg-suffix', 'agg-scenarios']))
    md += '# 跨篇藥名索引\n\n由 `compile_wiki.py` 從所有類別頁的藥物欄自動彙整。出現在兩頁以上的藥物，代表它在不同系統都有角色。\n\n'
    md += f'共 {len(drug_pages)} 個藥名；其中 {sum(1 for v in drug_pages.values() if len(v) > 1)} 個跨兩頁以上。\n\n'
    md += '| 藥名 | 出現頁數 | 類別頁 |\n| --- | --- | --- |\n'
    for d in sorted(drug_pages, key=str.lower):
        ps = drug_pages[d]
        md += f"| {d} | {len(ps)} | " + '、'.join(f"[[{p}|{by_id[p]['title']}]]" for p in ps) + ' |\n'
    open(os.path.join(WIKI, 'agg-drug-index.md'), 'w', encoding='utf-8').write(md)

    # 彙整頁：字尾
    md = fm(dict(id='agg-suffix', title='字尾辨識總表', type='aggregate',
                 sources=sorted({r[3] for r in suffix_rows}), related=['agg-drug-index']))
    md += '# 字尾辨識總表\n\n合併 12 篇講義的「字尾辨識法」。同一字尾在不同篇重複出現時保留各自的例子。\n\n'
    md += '| 字尾 | 類別 | 例子 | 來源 |\n| --- | --- | --- | --- |\n'
    for r in sorted(suffix_rows, key=lambda r: r[0].lower()):
        md += f'| {r[0]} | {r[1]} | {r[2]} | 〔{r[3]}〕 |\n'
    open(os.path.join(WIKI, 'agg-suffix.md'), 'w', encoding='utf-8').write(md)

    # 彙整頁：臨床情境
    md = fm(dict(id='agg-scenarios', title='臨床情境總表', type='aggregate',
                 sources=sorted({r[2] for r in scen_rows}), related=['agg-drug-index']))
    md += '# 臨床情境總表\n\n合併 12 篇講義最後一節的情境表。\n\n| 情境 | 常用藥物與注意 | 講義 |\n| --- | --- | --- |\n'
    for r in scen_rows:
        md += f'| {r[0]} | {r[1]} | {r[3]}〔{r[2]}〕 |\n'
    open(os.path.join(WIKI, 'agg-scenarios.md'), 'w', encoding='utf-8').write(md)

    # index.md
    concepts = []
    for f in sorted(glob.glob(os.path.join(WIKI, 'concept-*.md'))):
        t = open(f, encoding='utf-8').read()
        title = re.search(r'^title: (.+)$', t, re.M).group(1)
        summ = re.search(r'^summary: (.+)$', t, re.M)
        concepts.append((os.path.basename(f)[:-3], title, summ.group(1) if summ else ''))
    md = fm(dict(id='index', title='Wiki 目錄', type='index', sources=[], related=[]))
    md += '# 臺灣常用藥物 LLM Wiki：目錄\n\n'
    md += f'來源：{len(chapters)} 篇講義（`raw/`）。頁面：{len(concepts)} 個概念頁、{len(classes)} 個類別頁、3 個彙整頁。\n\n'
    md += '## 概念頁（AI 撰寫，跨篇觀念）\n\n' + ''.join(f'- [[{i}|{t}]]：{s}\n' for i, t, s in concepts) + '\n'
    md += '## 彙整頁（腳本產生）\n\n- [[agg-drug-index|跨篇藥名索引]]\n- [[agg-suffix|字尾辨識總表]]\n- [[agg-scenarios|臨床情境總表]]\n\n'
    md += '## 類別頁（依講義）\n\n'
    for nn, stem, h1, short in chapters:
        cs = [c for c in classes if c['nn'] == nn]
        md += f'### {nn} {short}\n\n' + ''.join(f"- [[{c['id']}|{c['title']}]]\n" for c in cs) + '\n'
    open(os.path.join(WIKI, 'index.md'), 'w', encoding='utf-8').write(md)

    print(f'chapters={len(chapters)} classes={len(classes)} drugs={len(drug_pages)} '
          f'multi={sum(1 for v in drug_pages.values() if len(v) > 1)} suffix_rows={len(suffix_rows)} '
          f'scenario_rows={len(scen_rows)} concepts={len(concepts)}')


if __name__ == '__main__':
    main()
