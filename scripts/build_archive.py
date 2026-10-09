"""Publish the approved archive; never substitute a preview for the original."""
import hashlib
import html
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = '20261009-bak-cultivation'
RECORD = ROOT / 'records' / SLUG
ZIP_NAME = '20261009_박_적심도식_정리_MD_HTML_전체자료.zip'
ZIP_HASH = '5d4c12e9b4962635f395065794dfe44c9f5899a1660be30591280e6a6363d920'
INPUT_ROOT = '20261009_박_적심도식_정리/'
EXPECTED = {
    'README.md': '139a3d75bc07d084cfed98ae1f83705b86d43b22ab5503bd5c273bc2ebeaaa64',
    'index.html': '1eb9dc7cc7909a5b8cff6f3c6738ffeec9a29259ad9b1484c64bbd5792050246',
    'archive-manifest.json': '3d8ffcec7c43dbb684772e1e8df25693841f16708bc9a0dc7a31274309a93686',
    'verification-report.md': 'dd81f562727ffe7f3812f71b1bdc721376eb3579aedfeda2be356573050879f2',
    'images/00_적심핵심도식.svg': '448587f1d34f8c7e9e3b26adfad9a8f25bbfb230a0292570675404727017c188',
    'images/01_적심전.svg': '7e704ac7ca71b7a595f4ca4ab34143eb2ebf75876935ab229546c3df8791a0d9',
    'images/02_절단위치.svg': '84f28d36edce66ffef43c1ee82257391112a248574ec9441848d428f575f3da8',
    'images/03_적심후.svg': 'e308f8d6e874ae0ed40be02abc0c7124fbf9a10b20285f9260ddfee01cc4cda5',
    'images/04_원본사진_박생육.jpg': 'bdae24af7d1bfaa1686868cc6e27d7c0ccda70e258bb904997f2664245564c52',
}
PHOTO = 'images/04_원본사진_박생육.jpg'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# Only the exact user-approved ZIP is accepted. No extraction of arbitrary paths/code.
source_zip = ROOT / 'zip' / ZIP_NAME
if source_zip.exists():
    data = source_zip.read_bytes()
    if sha(data) != ZIP_HASH:
        raise ValueError('Input ZIP hash differs from the approved source; refusing automatic import.')
    with zipfile.ZipFile(source_zip) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC verification failed')
        wanted = {INPUT_ROOT + name for name in EXPECTED}
        if set(z.namelist()) != wanted:
            raise ValueError('ZIP entry set differs from approved nine files')
        blobs = {name: z.read(INPUT_ROOT + name) for name in EXPECTED}
        for name, blob in blobs.items():
            if sha(blob) != EXPECTED[name]:
                raise ValueError('Source hash mismatch: ' + name)
        for name, blob in blobs.items():
            dest = RECORD / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob)
    originals = RECORD / 'originals'
    originals.mkdir(exist_ok=True)
    shutil.copy2(source_zip, originals / ZIP_NAME)
    print('IMPORTED: exact approved ZIP, nine source files. Input retained.')

missing = []
for name, digest in EXPECTED.items():
    file = RECORD / name
    if not file.exists():
        if name == PHOTO:
            missing.append(name)
            continue
        raise FileNotFoundError(name)
    if sha(file.read_bytes()) != digest:
        raise ValueError('Source bytes changed: ' + name)
complete = not missing
photo_count = 1 if complete else 0
metadata = {
    'schemaVersion': 1, 'project': '농업·농사', 'repository': 'softm/farm',
    'records': [{
        'id': SLUG, 'slug': SLUG,
        'listTitle': ZIP_NAME, 'sourceTitle': '박 적심 도식화 정리',
        'title': ZIP_NAME, 'date': '2026-10-09', 'dateBasis': 'archive_created',
        'eventDate': None, 'kind': '재배', 'visibility': 'public',
        'url': 'https://softm.github.io/farm/records/' + SLUG + '/',
        'repoUrl': 'https://github.com/softm/farm/tree/main/records/' + SLUG,
        'diagramCount': 4, 'originalPhotoCount': photo_count,
        'previewCount': 1, 'expectedOriginalPhotoCount': 1,
        'sourceFileCount': 9 - len(missing), 'expectedSourceFileCount': 9,
        'sourceIntegrityComplete': complete, 'missingFiles': missing,
        'status': 'source-complete' if complete else 'original-upload-pending',
        'description': '적심 전 → 절단 위치 → 적심 후 아들줄기. 도식 4개 중심의 원본 정리.'
    }]
}
save_json(ROOT / 'archive-index.json', metadata)
site = ROOT / '_site'
if site.exists():
    shutil.rmtree(site)
site.mkdir()
shutil.copy2(ROOT / 'index.html', site / 'index.html')
shutil.copy2(ROOT / 'archive-index.json', site / 'archive-index.json')
(site / '.nojekyll').write_text('', encoding='utf-8')
shutil.copytree(ROOT / 'records', site / 'records')
record_site = site / 'records' / SLUG
source_html = (RECORD / 'index.html').read_text(encoding='utf-8')
notice = ('도식 4개 · 원본 사진 1장 · 원본 파일 해시 일치' if complete else
          '원본 사진 업로드 대기: 아래 사진은 320px 미리보기이며 원본을 대체하지 않습니다. 도식 4개는 원본과 같습니다.')
nav = '<nav class="archive-nav"><a href="../../">농업·농사</a> · <a href="https://softm.github.io/projects/">전체 프로젝트</a> · <a href="readme.html">MD 읽기</a> · <a href="files.html">파일·검증</a> · <a href="https://github.com/softm/farm">farm</a></nav>'
styles = '<style>*{box-sizing:border-box}header h1{color:#fff}main{padding:16px}section{padding:18px}.grid{grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr))}.card{min-width:0}img{max-width:100%}.archive-nav{background:#fff;padding:12px 18px;line-height:2}.archive-notice{margin:12px 16px;padding:12px;border:1px solid #bbcabd;border-radius:8px;background:#fff}table{display:block;overflow-x:auto}dialog{max-height:96vh}.lightbox-wrap img{max-width:94vw;height:auto}a{overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
output = source_html.replace('</head>', styles + '</head>')
output = output.replace('<body>', '<body>' + nav + '<p class="archive-notice">' + notice + '</p>')
output = output.replace('이 파일은 ZIP 없이 단독으로 열어도 이미지가 보이도록 상대경로로 구성했습니다.', '입력 ZIP의 본문과 도식을 보존했습니다. 오프라인에서는 전체 폴더를 함께 보관하세요. 기록의 날짜는 정리일이며 실제 적심 작업일은 확인되지 않았습니다.')
if not complete:
    output = output.replace('src="' + PHOTO + '" alt="박 생육 원본 사진"', 'src="images/photo-preview.webp" alt="박 생육 사진 320px 미리보기 — 원본 업로드 대기"')
    output = output.replace('<h2>원본 사진 참고</h2>', '<h2>사진 미리보기 · 원본 업로드 대기</h2>')
    output = output.replace('<h2>포함 파일</h2>', '<h2>입력 ZIP의 파일 목록 · 실제 공개 상태는 파일·검증 참조</h2>')
# Enhance the served copy only; approved input HTML remains byte-identical.
viewer_script = r"""<script>(()=>{const d=document.getElementById('lightbox'),v=document.getElementById('lightboxImg'),all=[...document.querySelectorAll('img.zoomable')];let i=0;const bar=document.createElement('div');bar.style.cssText='padding:10px;display:flex;gap:12px;flex-wrap:wrap;background:white;color:#222';bar.innerHTML='<button id="img-prev" aria-label="이전 이미지">이전</button><span id="img-count"></span><button id="img-next" aria-label="다음 이미지">다음</button><a id="img-source" target="_blank" rel="noopener">이미지 파일 열기</a>';d.append(bar);function set(n){i=(n+all.length)%all.length;v.src=all[i].src;v.alt=all[i].alt;document.getElementById('img-count').textContent=(i+1)+' / '+all.length;document.getElementById('img-source').href=v.src}all.forEach((im,n)=>{im.tabIndex=0;im.addEventListener('click',()=>set(n));im.addEventListener('keydown',e=>{if(e.key==='Enter'){im.click();e.preventDefault()}})});document.getElementById('img-prev').onclick=()=>set(i-1);document.getElementById('img-next').onclick=()=>set(i+1);d.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'){set(i-1);e.preventDefault()}if(e.key==='ArrowRight'){set(i+1);e.preventDefault()}})})();</script>"""
output = output.replace('</body>', viewer_script + '</body>')
(record_site / 'index.html').write_text(output, encoding='utf-8')

# Plain-text views do not execute source code and also work offline.
def viewer(title, body):
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(title) + '</title><style>body{font-family:system-ui;max-width:1000px;margin:auto;padding:20px;line-height:1.7}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}td,th{padding:8px;border:1px solid #ddd;text-align:left;overflow-wrap:anywhere}</style><p><a href="./">기록으로</a> · <a href="../../">농업·농사</a></p><h1>' + html.escape(title) + '</h1>' + body + '</html>'
(record_site / 'readme.html').write_text(viewer('박 적심 도식화 정리 · Markdown 원문', '<p>' + notice + '</p><pre>' + html.escape((RECORD / 'README.md').read_text(encoding='utf-8')) + '</pre><a href="README.md" download>MD 다운로드</a>'), encoding='utf-8')
rows = []
for name in EXPECTED:
    f = RECORD / name
    label = '<a href="' + html.escape(name, quote=True) + '">' + html.escape(name) + '</a>' if f.exists() else html.escape(name)
    rows.append('<tr><td>' + label + '</td><td>' + (str(f.stat().st_size) + ' bytes · SHA-256 일치' if f.exists() else '원본 업로드 대기') + '</td></tr>')
body = '<p>' + notice + '</p><table><tr><th>원본 파일</th><th>공개 상태</th></tr>' + ''.join(rows) + '</table>'
if (record_site / 'originals' / ZIP_NAME).exists():
    body += '<p><a href="originals/' + ZIP_NAME + '" download>입력 ZIP 원본 다운로드</a></p>'
body += '<p>도식은 기존 정리본의 개념도입니다. 실제 잎 배열·마디 간격·사진 속 절단 지점을 확정하는 실측 도면은 아닙니다.</p>'
(record_site / 'files.html').write_text(viewer('파일 및 원본 검증', body), encoding='utf-8')

published = []
for f in sorted(site.rglob('*')):
    if f.is_file():
        published.append({'path': f.relative_to(site).as_posix(), 'size': f.stat().st_size, 'sha256': sha(f.read_bytes())})
report = {'sourceIntegrityComplete': complete, 'missingFiles': missing, 'publishedFileCount': len(published), 'files': published}
save_json(ROOT / 'build-verification.json', report)
print(json.dumps({'sourceIntegrityComplete': complete, 'missingFiles': missing, 'diagramCount': 4, 'originalPhotoCount': photo_count, 'publishedFileCount': len(published)}, ensure_ascii=False))
