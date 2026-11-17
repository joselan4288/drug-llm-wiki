#!/usr/bin/env python3
"""Check：檢查 slides/index.html 是否只用到 Wiki 裡有的內容。

  S1 每張投影片都要有 data-cite，且引用的 Wiki 頁存在
  S2 投影片中的英文藥名／商品名，必須出現在該張引用的 Wiki 頁中
  S3 投影片中的「數字＋單位」（劑量、時間），必須出現在該張引用的 Wiki 頁中
  S4 投影片中連到 ../wiki.html#<id> 的連結必須指向存在的頁面
  S5 繁體中文：簡體字與「台灣」
  W6（警告）中文句子與引用頁的 4-gram 重疊度 < 25%：可能是生成時自己加的內容，需人工確認

用法：python3 scripts/check_slides.py   （結束碼 0＝通過）
"""
import os, re, sys, html

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
WIKI = os.path.join(ROOT, 'wiki')
SLIDES = os.path.join(ROOT, 'slides', 'index.html')
DRUG = re.compile(r'(?<![A-Za-z])[A-Z][a-z][a-zA-Z]{3,}(?![A-Za-z])')
NUM = re.compile(r'\d+(?:\.\d+)?(?:[–-]\d+(?:\.\d+)?)?\s*(?:mg/kg|mg/mL|mg|g|%|分鐘|小時|天|秒|μg)')
SIMPLIFIED = set('这们药么为说时还发处应该经过对与从会样点种关进实现话问题请将让门见视测选简书长头剂疗')
IGNORE = {'Wiki', 'Noto', 'Sans', 'Serif', 'Mono', 'JetBrains'}


def ngram_overlap(sentence, source, n=4):
    """句子的中文 n-gram 有多少比例出現在來源裡（0–1）。"""
    s = re.sub(r'[^\u4e00-\u9fff]', '', sentence)
    if len(s) < n:
        return 1.0
    src = re.sub(r'[^\u4e00-\u9fff]', '', source)
    grams = [s[i:i + n] for i in range(len(s) - n + 1)]
    return sum(g in src for g in grams) / len(grams)


def unsupported_sentences(text, source, threshold=0.25, min_len=8):
    out = []
    for sent in re.split(r'[。；！？\n]|——', text):
        han = re.sub(r'[^\u4e00-\u9fff]', '', sent)
        if len(han) >= min_len and ngram_overlap(sent, source) < threshold:
            out.append(sent.strip())
    return out


def text_of(fragment):
    fragment = re.sub(r'<(title|desc)[^>]*>.*?</\1>', ' ', fragment, flags=re.S)
    fragment = re.sub(r'<[^>]+>', ' ', fragment)
    return html.unescape(re.sub(r'\s+', ' ', fragment))


def main():
    pages = {f[:-3]: open(os.path.join(WIKI, f), encoding='utf-8').read()
             for f in os.listdir(WIKI) if f.endswith('.md')}
    src = open(SLIDES, encoding='utf-8').read()
    secs = re.findall(r'<section class="slide"([^>]*)>(.*?)</section>', src, re.S)
    errors, warnings = [], []
    for i, (attrs, body) in enumerate(secs, 1):
        m = re.search(r'data-cite="([^"]*)"', attrs)
        ids = [x.strip() for x in m.group(1).split(',')] if m else []
        if not ids:
            errors.append(f'[S1] 第 {i} 張：沒有 data-cite'); continue
        for pid in ids:
            if pid not in pages:
                errors.append(f'[S1] 第 {i} 張：引用的頁面 {pid} 不存在')
        cited = '\n'.join(pages.get(p, '') for p in ids)
        if ids == ['index']:
            cited = '\n'.join(pages.values())  # 標題與總結頁：允許整個 Wiki
        t = text_of(body)
        for d in sorted(set(DRUG.findall(t)) - IGNORE):
            if d not in cited:
                errors.append(f'[S2] 第 {i} 張：「{d}」不在引用頁 {",".join(ids)} 中')
        for n in sorted(set(NUM.findall(t))):
            if n.replace(' ', '') not in cited.replace(' ', ''):
                errors.append(f'[S3] 第 {i} 張：數字「{n}」不在引用頁 {",".join(ids)} 中')
        for link in re.findall(r'\.\./wiki\.html#([\w-]+)', body):
            if link not in pages:
                errors.append(f'[S4] 第 {i} 張：連結 wiki.html#{link} 不存在')
        for sent in unsupported_sentences(t, cited):
            warnings.append(f'[W6] 第 {i} 張：「{sent[:40]}」與引用頁重疊度低')
        bad = sorted({c for c in t if c in SIMPLIFIED})
        if bad or '台灣' in t:
            errors.append(f"[S5] 第 {i} 張：疑似簡體字或「台灣」：{''.join(bad)}")
    for e in errors + warnings:
        print(e)
    print(f'\n投影片 {len(secs)} 張；錯誤 {len(errors)}；警告 {len(warnings)}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
