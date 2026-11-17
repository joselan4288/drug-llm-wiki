#!/usr/bin/env python3
"""Lint：檢查 wiki/ 是否符合 CLAUDE.md 的規則。

檢查項目
  L1 frontmatter：id 與檔名相同、有 title／type／sources
  L2 斷連結：[[id]] 指向不存在的頁面
  L3 孤兒頁：沒有任何頁面連進來（index、log 除外）
  L4 來源標記：〔raw檔名#中文序號〕 必須對應到 raw/ 中真的存在的 H2 章節
  L5 缺來源：概念頁中含事實的段落，本身或下一段沒有來源標記（以「推理」開頭、或不含藥名與數字的「說明」段落除外）
  L6 事實比對：概念頁每段出現的藥名（英文學名）與「數字＋單位」，必須出現在該段引用的 raw 章節裡
  L7 frontmatter 的 sources 要包含本文用到的所有來源
  L8 繁體中文：簡體字與「台灣」
  W9（警告）概念頁中文句子與引用 raw 章節的 4-gram 重疊度 < 25%：可能是撰寫時自己加的內容

用法：python3 scripts/lint_wiki.py [--quiet]
結束碼 0＝全部通過；1＝有錯誤。
"""
import os, re, glob, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RAW, WIKI = os.path.join(ROOT, 'raw'), os.path.join(ROOT, 'wiki')
SIMPLIFIED = set('这们药么为说时还发处应该经过对与从会样点种关进实现话问题请将让门见视测选简书长头剂疗')
TAG = re.compile(r'〔([0-9]{2}-[a-z-]+)#([一二三四五六七八九十]+)〕')
LINK = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]*)?\]\]')
DRUG = re.compile(r'(?<![A-Za-z])[A-Z][a-z][a-zA-Z]{3,}(?![A-Za-z])')
NUM = re.compile(r'\d+(?:\.\d+)?(?:[–-]\d+(?:\.\d+)?)?\s*(?:mg/kg|mg/mL|mg|g|%|分鐘|小時|天|秒|μg)')
IGNORE_WORDS = {'Wiki', 'Gq', 'Gi', 'Gs', 'Track', 'Class'}

errors = []
warnings = []


def ngram_overlap(sentence, source, n=4):
    s = re.sub(r'[^\u4e00-\u9fff]', '', sentence)
    if len(s) < n:
        return 1.0
    src = re.sub(r'[^\u4e00-\u9fff]', '', source)
    grams = [s[i:i + n] for i in range(len(s) - n + 1)]
    return sum(g in src for g in grams) / len(grams)


def err(code, page, msg):
    errors.append(f'[{code}] {page}: {msg}')


def raw_sections():
    secs = {}
    for f in glob.glob(os.path.join(RAW, '*.md')):
        stem = os.path.basename(f)[:-3]
        parts = re.split(r'^## (.+)$', open(f, encoding='utf-8').read(), flags=re.M)
        for i in range(1, len(parts), 2):
            m = re.match(r'^([一二三四五六七八九十]+)、', parts[i])
            if m:
                secs[(stem, m.group(1))] = parts[i] + '\n' + parts[i + 1]
    return secs


def parse(path):
    t = open(path, encoding='utf-8').read()
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', t, re.S)
    if not m:
        return None, t
    meta = {}
    for line in m.group(1).split('\n'):
        k, _, v = line.partition(': ')
        v = v.strip()
        meta[k.strip()] = [x.strip() for x in v[1:-1].split(',') if x.strip()] if v.startswith('[') else v
    return meta, m.group(2)


def main():
    secs = raw_sections()
    pages = {}
    for f in sorted(glob.glob(os.path.join(WIKI, '*.md'))):
        meta, body = parse(f)
        pages[os.path.basename(f)[:-3]] = (meta, body)

    inbound = {p: 0 for p in pages}
    for pid, (meta, body) in pages.items():
        # L1
        if meta is None:
            err('L1', pid, '缺少 frontmatter'); continue
        if meta.get('id') != pid:
            err('L1', pid, f"id「{meta.get('id')}」與檔名不同")
        for k in ('title', 'type', 'sources'):
            if k not in meta:
                err('L1', pid, f'缺少 {k}')
        # L2
        for target in LINK.findall(body) + list(meta.get('related', [])):
            if target not in pages:
                err('L2', pid, f'連到不存在的頁面 [[{target}]]')
            elif target != pid:
                inbound[target] += 1
        # L4 + L7
        used = set()
        for stem, num in TAG.findall(body):
            used.add(f'{stem}#{num}')
            if (stem, num) not in secs:
                err('L4', pid, f'來源〔{stem}#{num}〕不存在於 raw/')
        declared = set(meta.get('sources', []))
        for u in (sorted(used - declared) if meta.get('type') != 'log' else []):
            err('L7', pid, f'本文用了〔{u}〕但 frontmatter sources 沒有列')
        # L8
        for i, line in enumerate(body.split('\n'), 1):
            bad = sorted({c for c in line if c in SIMPLIFIED})
            if bad:
                err('L8', pid, f"第 {i} 行疑似簡體字：{''.join(bad)}")
            if '台灣' in line:
                err('L8', pid, f'第 {i} 行「台灣」應為「臺灣」')

        if meta.get('type') != 'concept':
            continue
        # L5 + L6：以空行切段
        blocks = [b.strip() for b in re.split(r'\n\s*\n', body) if b.strip()]
        for i, b in enumerate(blocks):
            if b.startswith('#') or re.fullmatch(r'(〔[^〕]+〕\s*)+', b):
                continue
            if re.match(r'^(> )?推理', b) or '推理，非來源原文' in b.split('\n')[0]:
                continue
            if re.match(r'^說明', b) and not (DRUG.search(b) or NUM.search(b)):
                continue  # 一般說明：不含藥名與數字才可免標來源
            text = re.sub(LINK, '', b)
            if not re.search(r'[A-Za-z0-9一-鿿]', text):
                continue
            tags = TAG.findall(b)
            if not tags and i + 1 < len(blocks) and re.fullmatch(r'(〔[^〕]+〕\s*)+', blocks[i + 1]):
                tags = TAG.findall(blocks[i + 1])
            factual = DRUG.search(text) or NUM.search(text) or len(re.sub(r'\s', '', text)) > 40
            if not tags:
                if factual and not re.match(r'^(下一步|相關|情境速查|中毒表現)', text) and '[[' not in b:
                    err('L5', pid, f'段落缺來源標記：「{text[:30]}…」')
                continue
            cited = '\n'.join(secs.get(t, '') for t in tags)
            for d in sorted(set(DRUG.findall(text)) - IGNORE_WORDS):
                if d not in cited:
                    err('L6', pid, f"藥名「{d}」不在引用的來源 {'、'.join('#'.join(t) for t in tags)} 中")
            for sent in re.split(r'[。；！？\n]', re.sub(r'〔[^〕]+〕', '', text)):
                if len(re.sub(r'[^\u4e00-\u9fff]', '', sent)) >= 8 and ngram_overlap(sent, cited) < 0.25:
                    warnings.append(f'[W9] {pid}: 「{sent.strip()[:36]}」與引用來源重疊度低')
            for n in sorted(set(NUM.findall(text))):
                if n.replace(' ', '') not in cited.replace(' ', ''):
                    err('L6', pid, f"數字「{n}」不在引用的來源 {'、'.join('#'.join(t) for t in tags)} 中")

    # L3
    for p, n in inbound.items():
        if n == 0 and p not in ('index', 'log'):
            err('L3', p, '孤兒頁：沒有任何頁面連進來')

    counts = {}
    for e in errors:
        counts[e[1:3]] = counts.get(e[1:3], 0) + 1
    if '--quiet' not in sys.argv:
        for e in errors + warnings:
            print(e)
    summary = '、'.join(f'{k} {v} 個' for k, v in sorted(counts.items())) or '無'
    print(f'\n頁面 {len(pages)}；錯誤 {len(errors)}（{summary}）；警告 {len(warnings)}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
