#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from pathlib import Path


def chapter_number(path: Path) -> int:
    match = re.search(r"第\s*([0-9０-９一二三四五六七八九十百千万零〇两]+)\s*章", path.stem)
    if not match:
        return 10**9
    raw = match.group(1)
    normalized = raw.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    if normalized.isdigit():
        return int(normalized)
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000}
    total = 0
    section = 0
    number = 0
    for char in raw:
        if char in digits:
            number = digits[char]
        elif char in units:
            unit = units[char]
            if unit == 10000:
                total += (section + number) * unit
                section = 0
            else:
                section += (number or 1) * unit
            number = 0
    return total + section + number


def slugify(name: str) -> str:
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    ascii_part = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return ascii_part or f"book-{digest}"


def markdown_to_html(text: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            blocks.append(f"<p>{'<br>'.join(paragraph)}</p>")
            paragraph.clear()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush()
            level = min(len(heading.group(1)), 3)
            blocks.append(f"<h{level}>{html.escape(heading.group(2))}</h{level}>")
        elif line == "---":
            flush()
            blocks.append("<hr>")
        else:
            paragraph.append(html.escape(line))
    flush()
    return "\n".join(blocks)


def discover_books(source: Path) -> list[dict[str, object]]:
    books: list[dict[str, object]] = []
    for book_dir in sorted(source.iterdir() if source.exists() else []):
        chapters_dir = book_dir / "chapters"
        if not chapters_dir.is_dir():
            continue
        files = sorted(chapters_dir.glob("*.md"), key=lambda item: (chapter_number(item), item.name))
        if not files:
            continue
        slug = slugify(book_dir.name)
        books.append({
            "title": book_dir.name,
            "slug": slug,
            "count": len(files),
            "files": files,
        })
    return books


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: object) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def build(source: Path, output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    books = discover_books(source)
    catalog: list[dict[str, object]] = []

    for book in books:
        title = str(book["title"])
        slug = str(book["slug"])
        files = list(book["files"])
        chapters: list[dict[str, object]] = []
        for index, file in enumerate(files, start=1):
            chapter_title = file.stem.replace("_", " ")
            raw = file.read_text(encoding="utf-8")
            chapters.append({"index": index, "title": chapter_title, "path": f"data/books/{slug}/{index:04d}.json"})
            write_json(output / "data" / "books" / slug / f"{index:04d}.json", {
                "bookTitle": title,
                "bookSlug": slug,
                "index": index,
                "title": chapter_title,
                "html": markdown_to_html(raw),
                "prev": index - 1 if index > 1 else None,
                "next": index + 1 if index < len(files) else None,
            })
        write_json(output / "data" / "books" / slug / "chapters.json", chapters)
        catalog.append({"title": title, "slug": slug, "count": len(files), "chaptersPath": f"data/books/{slug}/chapters.json"})

    write_json(output / "data" / "catalog.json", catalog)
    write_text(output / "index.html", INDEX_HTML)
    write_text(output / "assets" / "app.css", APP_CSS)
    write_text(output / "assets" / "app.js", APP_JS)
    write_text(output / ".nojekyll", "")


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>小说阅读器</title>
  <link rel="stylesheet" href="assets/app.css">
</head>
<body>
  <header id="header">
    <div class="topbar">
      <button id="backBtn" class="btn hidden">返回</button>
      <div id="title" class="brand">小说阅读器</div>
      <button id="darkBtn" class="btn">夜间</button>
    </div>
  </header>
  <main id="app" class="wrap"></main>
  <nav id="toolbar" class="toolbar hidden">
    <div class="toolbar-inner">
      <button id="prevBtn" class="btn">上一章</button>
      <button id="smallBtn" class="btn">A-</button>
      <button id="largeBtn" class="btn">A+</button>
      <button id="nextBtn" class="btn">下一章</button>
    </div>
  </nav>
  <script src="assets/app.js"></script>
</body>
</html>
"""

APP_CSS = """:root{color-scheme:light dark;--bg:#f7f1e8;--paper:#fffaf2;--text:#2d241b;--muted:#8a7662;--line:#eadcca;--accent:#8b4513}body.dark{--bg:#151515;--paper:#202020;--text:#e9dfd1;--muted:#a69683;--line:#39332c;--accent:#d49a62}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Serif SC","Microsoft YaHei",sans-serif}button{font:inherit}a{color:inherit;text-decoration:none}.hidden{display:none!important}.wrap{width:min(100%,860px);margin:0 auto;padding:16px max(16px,env(safe-area-inset-right)) 96px max(16px,env(safe-area-inset-left))}.card{background:var(--paper);border:1px solid var(--line);border-radius:18px;box-shadow:0 8px 28px rgba(70,42,15,.08)}header{position:sticky;top:0;z-index:3;backdrop-filter:blur(14px);background:color-mix(in srgb,var(--bg) 86%,transparent);border-bottom:1px solid var(--line);transition:transform .3s ease}.topbar{width:min(100%,860px);margin:0 auto;padding:10px 16px;display:flex;gap:10px;align-items:center;justify-content:space-between}.brand{font-weight:800;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.btn{border:1px solid var(--line);background:var(--paper);color:var(--text);border-radius:999px;padding:9px 13px;font-size:14px}.grid{display:grid;gap:12px}.book,.chapter{display:block;padding:16px}.chapter{width:100%;text-align:left;border:0;border-bottom:1px solid var(--line);border-radius:0;background:transparent;color:var(--text)}.chapter:last-child{border-bottom:0}.muted{color:var(--muted);font-size:13px}.reader{padding:22px 18px;font-size:var(--reader-size,20px);line-height:2.05;letter-spacing:.03em}.reader h1,.reader h2,.reader h3{line-height:1.35;text-align:center;margin:8px 0 28px;letter-spacing:0}.reader p{margin:0 0 1.1em;text-indent:2em}.reader hr{border:0;border-top:1px solid var(--line);margin:24px 0}.toolbar{position:fixed;left:0;right:0;bottom:0;z-index:4;padding:10px max(12px,env(safe-area-inset-right)) max(10px,env(safe-area-inset-bottom)) max(12px,env(safe-area-inset-left));background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(14px);border-top:1px solid var(--line);transition:transform .3s ease}.toolbar-inner{width:min(100%,860px);margin:0 auto;display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px}.toolbar .btn{text-align:center;padding:11px 6px}@media (min-width:720px){.reader{padding:36px 46px}}body.immersive.immersive-hidden header{transform:translateY(-100%)}body.immersive.immersive-hidden .toolbar{transform:translateY(100%)}body.immersive.immersive-hidden .wrap{padding-top:16px;padding-bottom:16px}"""

APP_JS = r"""const app=document.querySelector('#app');const titleEl=document.querySelector('#title');const backBtn=document.querySelector('#backBtn');const toolbar=document.querySelector('#toolbar');const darkBtn=document.querySelector('#darkBtn');const header=document.querySelector('#header');let navHandler=null;const prevBtn=document.querySelector('#prevBtn');const nextBtn=document.querySelector('#nextBtn');const smallBtn=document.querySelector('#smallBtn');const largeBtn=document.querySelector('#largeBtn');let state={catalog:[],chapters:[],book:null,chapter:null};function applyPrefs(){if(localStorage.getItem('novel:dark')==='1')document.body.classList.add('dark');document.documentElement.style.setProperty('--reader-size',(localStorage.getItem('novel:size')||'20')+'px');localStorage.removeItem('novel:fullscreen')}function setDark(){document.body.classList.toggle('dark');localStorage.setItem('novel:dark',document.body.classList.contains('dark')?'1':'0')}function applyImmersive(on){document.body.classList.toggle('immersive',on);if(!on)document.body.classList.remove('immersive-hidden');localStorage.setItem('novel:immersive',on?'1':'0')}function toggleImmersiveUI(){document.body.classList.toggle('immersive-hidden');localStorage.setItem('novel:immersive',document.body.classList.contains('immersive-hidden')?'1':'0')}function fontSize(delta){const current=parseInt(localStorage.getItem('novel:size')||'20',10);const next=Math.max(16,Math.min(28,current+delta));localStorage.setItem('novel:size',String(next));applyPrefs()}async function loadJson(path){const res=await fetch(path);if(!res.ok)throw new Error('\u52a0\u8f7d\u5931\u8d25: '+path);return await res.json()}function go(hash){location.hash=hash}function routeParts(){return location.hash.replace(/^#/,'').split('/').filter(Boolean)}function showLoading(){app.innerHTML='<section class="card book">\u52a0\u8f7d\u4e2d...</section>'}function renderHome(){document.body.classList.remove('immersive','immersive-hidden');navHandler=null;toolbar.classList.add('hidden');backBtn.classList.add('hidden');titleEl.textContent='\u5c0f\u8bf4\u9605\u8bfb\u5668';const items=state.catalog.map(book=>`<button class="book card" onclick="go('/book/${book.slug}')"><strong>${escapeHtml(book.title)}</strong><div class="muted">${book.count} \u7ae0</div></button>`).join('')||'<section class="book card">\u6ca1\u6709\u627e\u5230\u5c0f\u8bf4\u6570\u636e\u3002</section>';app.innerHTML=`<section class="grid"><h2>\u9009\u62e9\u5c0f\u8bf4</h2>${items}</section>`}async function renderBook(slug){document.body.classList.remove('immersive','immersive-hidden');toolbar.classList.add('hidden');backBtn.classList.remove('hidden');navHandler=()=>go('/');const book=state.catalog.find(item=>item.slug===slug);if(!book){renderNotFound();return}state.book=book;titleEl.textContent=book.title;showLoading();state.chapters=await loadJson(book.chaptersPath);const last=localStorage.getItem('novel:last:'+slug);const resume=last?`<button class="book card" onclick="go('/read/${slug}/${last}')"><strong>\u7ee7\u7eed\u9605\u8bfb</strong><div class="muted">\u7b2c ${last} \u7ae0</div></button>`:'';const items=state.chapters.map(chapter=>`<button class="chapter" onclick="go('/read/${slug}/${chapter.index}')"><span>${escapeHtml(chapter.title)}</span><div class="muted">\u7b2c ${chapter.index} \u7ae0</div></button>`).join('');app.innerHTML=`<section class="grid"><h2>\u76ee\u5f55</h2>${resume}<div class="card">${items}</div></section>`}async function renderChapter(slug,index){backBtn.classList.remove('hidden');navHandler=()=>go('/book/'+slug);toolbar.classList.remove('hidden');const book=state.catalog.find(item=>item.slug===slug);if(!book){renderNotFound();return}if(!state.chapters.length||state.book?.slug!==slug){state.book=book;state.chapters=await loadJson(book.chaptersPath)}const meta=state.chapters.find(item=>item.index===index);if(!meta){renderNotFound();return}showLoading();const chapter=await loadJson(meta.path);state.chapter=chapter;titleEl.textContent=chapter.title;app.innerHTML=`<article class="reader card">${chapter.html}</article>`;localStorage.setItem('novel:last:'+slug,String(index));prevBtn.disabled=!chapter.prev;nextBtn.disabled=!chapter.next;prevBtn.onclick=()=>chapter.prev?go(`/read/${slug}/${chapter.prev}`):go('/book/'+slug);nextBtn.onclick=()=>chapter.next?go(`/read/${slug}/${chapter.next}`):go('/book/'+slug);window.scrollTo({top:0});document.body.classList.add('immersive');if(localStorage.getItem('novel:immersive')!=='0')setTimeout(function(){document.body.classList.add('immersive-hidden')},1500)}function renderNotFound(){document.body.classList.remove('immersive','immersive-hidden');navHandler=null;toolbar.classList.add('hidden');titleEl.textContent='\u672a\u627e\u5230';app.innerHTML='<section class="card book">\u9875\u9762\u4e0d\u5b58\u5728\u3002</section>'}async function router(){try{const parts=routeParts();if(!state.catalog.length)state.catalog=await loadJson('data/catalog.json');if(parts[0]==='book'&&parts[1])await renderBook(parts[1]);else if(parts[0]==='read'&&parts[1]&&parts[2])await renderChapter(parts[1],parseInt(parts[2],10));else renderHome()}catch(err){console.error(err);app.innerHTML='<section class="card book">\u52a0\u8f7d\u5931\u8d25\uff0c\u8bf7\u5237\u65b0\u9875\u9762\u91cd\u8bd5\u3002</section>'}}function escapeHtml(value){return String(value).replace(/[&<>"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]))}darkBtn.onclick=setDark;backBtn.onclick=function(){if(document.body.classList.contains('immersive')&&document.body.classList.contains('immersive-hidden')){document.body.classList.remove('immersive','immersive-hidden');localStorage.setItem('novel:immersive','0');return}if(navHandler)navHandler()};app.addEventListener('touchstart',function(e){if(!document.body.classList.contains('immersive'))return;var t=e.touches[0];var x=t.clientX,vw=window.innerWidth;if(document.body.classList.contains('immersive-hidden')){if(x<vw*0.15&&state.chapter?.prev)go('/read/'+state.book.slug+'/'+state.chapter.prev);else if(x>vw*0.85&&state.chapter?.next)go('/read/'+state.book.slug+'/'+state.chapter.next);else toggleImmersiveUI()}else{toggleImmersiveUI()}},{passive:true});app.addEventListener('click',function(e){if(!document.body.classList.contains('immersive'))return;if(e.target.closest('button,a,input'))return;if(e.sourceCapabilities&&e.sourceCapabilities.firesTouchEvents)return;var x=e.clientX,vw=window.innerWidth;if(document.body.classList.contains('immersive-hidden')){if(x<vw*0.15&&state.chapter?.prev)go('/read/'+state.book.slug+'/'+state.chapter.prev);else if(x>vw*0.85&&state.chapter?.next)go('/read/'+state.book.slug+'/'+state.chapter.next);else toggleImmersiveUI()}else{toggleImmersiveUI()}});smallBtn.onclick=()=>fontSize(-1);largeBtn.onclick=()=>fontSize(1);window.addEventListener('hashchange',router);applyPrefs();router();"""


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 GitHub Pages 静态小说阅读站")
    parser.add_argument("--source", type=Path, default=Path("../store/novel"), help="小说源目录，默认 ../store/novel")
    parser.add_argument("--output", type=Path, default=Path("docs"), help="输出目录，默认 docs")
    args = parser.parse_args()
    build(args.source.resolve(), args.output.resolve())
    print(f"已生成静态站：{args.output}")


if __name__ == "__main__":
    main()
