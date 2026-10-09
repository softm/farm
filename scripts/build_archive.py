"""Build the public farm archive from approved source bundles and committed records."""
import hashlib
import html
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / '_site'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

BAK = {
    'slug': '20261009-bak-cultivation',
    'zip_name': '20261009_박_적심도식_정리_MD_HTML_전체자료.zip',
    'zip_hash': '5d4c12e9b4962635f395065794dfe44c9f5899a1660be30591280e6a6363d920',
    'input_root': '20261009_박_적심도식_정리/',
    'expected': {
        'README.md': '139a3d75bc07d084cfed98ae1f83705b86d43b22ab5503bd5c273bc2ebeaaa64',
        'index.html': '1eb9dc7cc7909a5b8cff6f3c6738ffeec9a29259ad9b1484c64bbd5792050246',
        'archive-manifest.json': '3d8ffcec7c43dbb684772e1e8df25693841f16708bc9a0dc7a31274309a93686',
        'verification-report.md': 'dd81f562727ffe7f3812f71b1bdc721376eb3579aedfeda2be356573050879f2',
        'images/00_적심핵심도식.svg': '448587f1d34f8c7e9e3b26adfad9a8f25bbfb230a0292570675404727017c188',
        'images/01_적심전.svg': '7e704ac7ca71b7a595f4ca4ab34143eb2ebf75876935ab229546c3df8791a0d9',
        'images/02_절단위치.svg': '84f28d36edce66ffef43c1ee82257391112a248574ec9441848d428f575f3da8',
        'images/03_적심후.svg': 'e308f8d6e874ae0ed40be02abc0c7124fbf9a10b20285f9260ddfee01cc4cda5',
        'images/04_원본사진_박생육.jpg': 'bdae24af7d1bfaa1686868cc6e27d7c0ccda70e258bb904997f2664245564c52',
    },
    'optional_missing': {'images/04_원본사진_박생육.jpg'},
}

SPRINKLER = {
    'slug': '20261009-sprinkler-thread-guide',
    'zip_name': '20261009_스프링클러_배관_나사_규격_정리_MD_HTML_전체자료.zip',
    'zip_hash': '9938ab410763d27a0aa5d40e96fda2617dc7a44a660fdde30b69937b704a710c',
    'input_root': '20261009_스프링클러_배관_나사_규격_정리/',
    'expected': {
        'README.md': 'a192e6b7f5f2390ced35239cc5e5f6f1fb5c04b5fb1e4199ea2bfe2e2c2fc85d',
        'archive-manifest.json': 'fc0413cd77582b98472c4c79eaf2991cc016afd2f478001fe9b746af8ff71edd',
        'images/1787216371339.jpeg': 'dd02c30f2b6e49499a9b73b382f81abec495f19be8ff331b928b5dc0b388ecad',
        'images/1787216435706.jpeg': 'a56f1452cfdde8eb0af1dbd95648cb952d19e81776680944ccd0562a622063a6',
        'images/1787216990018.jpeg': 'a56f1452cfdde8eb0af1dbd95648cb952d19e81776680944ccd0562a622063a6',
        'index.html': '4f586fcdddc83867696408e0ead54db9144e543b89035e1f22f01b9b534621e3',
        'source-inventory.csv': '266a0b2a8c6ecf883227c5ca9dbbcd266018e31491bee1c355668b50447736c2',
        'verification-report.md': '8661ee947b1bbee00655ce60505d56f86520f9bfbcc0d3e5be2d4233a87a3c71',
    },
    'optional_missing': set(),
}

def import_approved(config):
    record = ROOT / 'records' / config['slug']
    source_zip = ROOT / 'zip' / config['zip_name']
    if not source_zip.exists():
        return False
    data = source_zip.read_bytes()
    if sha(data) != config['zip_hash']:
        raise ValueError('Input ZIP hash differs from approved source: ' + config['zip_name'])
    with zipfile.ZipFile(source_zip) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC verification failed: ' + config['zip_name'])
        wanted = {config['input_root'] + name for name in config['expected']}
        if set(z.namelist()) != wanted:
            raise ValueError('ZIP entry set differs from approved files: ' + config['zip_name'])
        blobs = {name: z.read(config['input_root'] + name) for name in config['expected']}
        for name, blob in blobs.items():
            if sha(blob) != config['expected'][name]:
                raise ValueError('Source hash mismatch: ' + name)
        if config['slug'] == SPRINKLER['slug']:
            # Remove superseded partial-deployment helpers before replacing with the completed source.
            for stale in ['missing-media.md']:
                p = record / stale
                if p.exists():
                    p.unlink()
            old_originals = record / 'originals'
            if old_originals.exists():
                shutil.rmtree(old_originals)
        for name, blob in blobs.items():
            dest = record / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob)
    originals = record / 'originals'
    originals.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_zip, originals / config['zip_name'])
    print('IMPORTED:', config['zip_name'])
    return True

def verify(config):
    record = ROOT / 'records' / config['slug']
    missing = []
    for name, digest in config['expected'].items():
        f = record / name
        if not f.exists():
            missing.append(name)
            continue
        if sha(f.read_bytes()) != digest:
            raise ValueError('Committed source bytes changed: ' + config['slug'] + '/' + name)
    disallowed = [x for x in missing if x not in config['optional_missing']]
    if disallowed:
        return False, missing
    return not missing, missing

import_approved(BAK)
import_approved(SPRINKLER)

bak_complete, bak_missing = verify(BAK)
spr_complete, spr_missing = verify(SPRINKLER)
bak_record = ROOT / 'records' / BAK['slug']
spr_record = ROOT / 'records' / SPRINKLER['slug']

metadata = {
    'schemaVersion': 2,
    'project': '농업·농사',
    'repository': 'softm/farm',
    'records': [
        {
            'id': BAK['slug'], 'slug': BAK['slug'],
            'listTitle': BAK['zip_name'], 'sourceTitle': '박 적심 도식화 정리',
            'title': BAK['zip_name'], 'date': '2026-10-09', 'dateBasis': 'archive_created',
            'eventDate': None, 'kind': '재배', 'visibility': 'public',
            'url': 'https://softm.github.io/farm/records/' + BAK['slug'] + '/',
            'repoUrl': 'https://github.com/softm/farm/tree/main/records/' + BAK['slug'],
            'diagramCount': 4, 'originalPhotoCount': 1 if bak_complete else 0,
            'previewCount': 1, 'expectedOriginalPhotoCount': 1,
            'sourceFileCount': len(BAK['expected']) - len(bak_missing),
            'expectedSourceFileCount': len(BAK['expected']),
            'sourceIntegrityComplete': bak_complete, 'missingFiles': bak_missing,
            'status': 'source-complete' if bak_complete else 'original-upload-pending',
            'description': '적심 전 → 절단 위치 → 적심 후 아들줄기. 도식 4개 중심의 원본 정리.'
        },
        {
            'id': SPRINKLER['slug'], 'slug': SPRINKLER['slug'],
            'listTitle': SPRINKLER['zip_name'],
            'sourceTitle': '스프링클러 배관 나사 규격 정리',
            'title': '스프링클러 배관 나사 규격 정리',
            'titleSource': 'user-override',
            'date': '2026-10-09', 'dateBasis': 'archive_created',
            'eventDate': None, 'kind': '관수·부품', 'visibility': 'public',
            'url': 'https://softm.github.io/farm/records/' + SPRINKLER['slug'] + '/',
            'repoUrl': 'https://github.com/softm/farm/tree/main/records/' + SPRINKLER['slug'],
            'originalImageCount': 3, 'uniqueOriginalImageCount': 2,
            'expectedOriginalImageCount': 3, 'previewCount': 0,
            'sourceFileCount': len(SPRINKLER['expected']) - len(spr_missing),
            'expectedSourceFileCount': len(SPRINKLER['expected']),
            'sourceIntegrityComplete': spr_complete, 'missingFiles': spr_missing,
            'status': 'source-complete' if spr_complete else 'source-incomplete',
            'description': '1/2″·3/4″·1″ 스프링클러 배관 나사 호칭과 수나사 외경 비교. 대화 첨부 이미지 3개와 원본 ZIP을 보존.'
        }
    ]
}
save_json(ROOT / 'archive-index.json', metadata)

if SITE.exists():
    shutil.rmtree(SITE)
SITE.mkdir()
shutil.copy2(ROOT / 'index.html', SITE / 'index.html')
shutil.copy2(ROOT / 'archive-index.json', SITE / 'archive-index.json')
(SITE / '.nojekyll').write_text('', encoding='utf-8')
shutil.copytree(ROOT / 'records', SITE / 'records')

def viewer(title, body):
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(title) + '</title><style>body{font-family:system-ui;max-width:1000px;margin:auto;padding:20px;line-height:1.7}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}td,th{padding:8px;border:1px solid #ddd;text-align:left;overflow-wrap:anywhere}img{max-width:100%;height:auto}</style><p><a href="./">기록으로</a> · <a href="../../">농업·농사</a></p><h1>' + html.escape(title) + '</h1>' + body + '</html>'

# Serve an enhanced copy for the legacy Bak source while leaving its approved source bytes unchanged.
bak_site = SITE / 'records' / BAK['slug']
source_html = (bak_record / 'index.html').read_text(encoding='utf-8')
notice = ('도식 4개 · 원본 사진 1장 · 원본 파일 해시 일치' if bak_complete else
          '원본 사진 업로드 대기: 아래 사진은 320px 미리보기이며 원본을 대체하지 않습니다. 도식 4개는 원본과 같습니다.')
nav = '<nav class="archive-nav"><a href="../../">농업·농사</a> · <a href="https://softm.github.io/projects/">전체 프로젝트</a> · <a href="readme.html">MD 읽기</a> · <a href="files.html">파일·검증</a> · <a href="https://github.com/softm/farm">farm</a></nav>'
styles = '<style>*{box-sizing:border-box}header h1{color:#fff}main{padding:16px}section{padding:18px}.grid{grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr))}.card{min-width:0}img{max-width:100%}.archive-nav{background:#fff;padding:12px 18px;line-height:2}.archive-notice{margin:12px 16px;padding:12px;border:1px solid #bbcabd;border-radius:8px;background:#fff}table{display:block;overflow-x:auto}dialog{max-height:96vh}.lightbox-wrap img{max-width:94vw;height:auto}a{overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
output = source_html.replace('</head>', styles + '</head>').replace('<body>', '<body>' + nav + '<p class="archive-notice">' + notice + '</p>')
if not bak_complete:
    photo = 'images/04_원본사진_박생육.jpg'
    output = output.replace('src="' + photo + '" alt="박 생육 원본 사진"', 'src="images/photo-preview.webp" alt="박 생육 사진 320px 미리보기 — 원본 업로드 대기"')
    output = output.replace('<h2>원본 사진 참고</h2>', '<h2>사진 미리보기 · 원본 업로드 대기</h2>')
viewer_script = r"""<script>(()=>{const d=document.getElementById('lightbox'),v=document.getElementById('lightboxImg'),all=[...document.querySelectorAll('img.zoomable')];let i=0;const bar=document.createElement('div');bar.style.cssText='padding:10px;display:flex;gap:12px;flex-wrap:wrap;background:white;color:#222';bar.innerHTML='<button id="img-prev">이전</button><span id="img-count"></span><button id="img-next">다음</button><a id="img-source" target="_blank" rel="noopener">이미지 파일 열기</a>';d.append(bar);function set(n){i=(n+all.length)%all.length;v.src=all[i].src;v.alt=all[i].alt;document.getElementById('img-count').textContent=(i+1)+' / '+all.length;document.getElementById('img-source').href=v.src}all.forEach((im,n)=>im.addEventListener('click',()=>set(n)));document.getElementById('img-prev').onclick=()=>set(i-1);document.getElementById('img-next').onclick=()=>set(i+1);d.addEventListener('keydown',e=>{if(e.key==='ArrowLeft')set(i-1);if(e.key==='ArrowRight')set(i+1)})})();</script>"""
(bak_site / 'index.html').write_text(output.replace('</body>', viewer_script + '</body>'), encoding='utf-8')
(bak_site / 'readme.html').write_text(viewer('박 적심 도식화 정리 · Markdown 원문', '<pre>' + html.escape((bak_record / 'README.md').read_text(encoding='utf-8')) + '</pre>'), encoding='utf-8')

# Completed sprinkler source: keep source HTML intact in the repository, enhance only the published copy with navigation.
spr_site = SITE / 'records' / SPRINKLER['slug']
spr_html = (spr_record / 'index.html').read_text(encoding='utf-8')
spr_nav = '<nav style="max-width:1040px;margin:auto;padding:12px 20px"><a href="../../">농업·농사</a> · <a href="https://softm.github.io/projects/farm/">중앙 농업 홈</a> · <a href="readme.html">MD 읽기</a> · <a href="files.html">파일·검증</a></nav>'
spr_html = spr_html.replace('<body>', '<body>' + spr_nav)
(spr_site / 'index.html').write_text(spr_html, encoding='utf-8')
(spr_site / 'readme.html').write_text(viewer('스프링클러 배관 나사 규격 정리 · Markdown', '<pre>' + html.escape((spr_record / 'README.md').read_text(encoding='utf-8')) + '</pre><p><a href="README.md" download>MD 원본 다운로드</a></p>'), encoding='utf-8')
rows = []
for name, digest in SPRINKLER['expected'].items():
    f = spr_record / name
    link = '<a href="' + html.escape(name, quote=True) + '">' + html.escape(name) + '</a>'
    rows.append('<tr><td>' + link + '</td><td>' + str(f.stat().st_size) + ' bytes</td><td>SHA-256 일치</td></tr>')
zip_path = spr_record / 'originals' / SPRINKLER['zip_name']
body = '<p>대화 첨부 이미지 3개(고유 이미지 2개)를 모두 파일명별로 보존했습니다.</p><table><tr><th>파일</th><th>크기</th><th>검증</th></tr>' + ''.join(rows) + '</table>'
if zip_path.exists():
    body += '<p><a href="originals/' + html.escape(SPRINKLER['zip_name'], quote=True) + '" download>원본 ZIP 다운로드</a> · ' + str(zip_path.stat().st_size) + ' bytes · SHA-256 ' + sha(zip_path.read_bytes()) + '</p>'
(spr_site / 'files.html').write_text(viewer('스프링클러 기록 · 파일 및 원본 검증', body), encoding='utf-8')

published = []
for f in sorted(SITE.rglob('*')):
    if f.is_file():
        published.append({'path': f.relative_to(SITE).as_posix(), 'size': f.stat().st_size, 'sha256': sha(f.read_bytes())})
report = {
    'records': {
        BAK['slug']: {'sourceIntegrityComplete': bak_complete, 'missingFiles': bak_missing},
        SPRINKLER['slug']: {'sourceIntegrityComplete': spr_complete, 'missingFiles': spr_missing, 'originalImageCount': 3, 'uniqueOriginalImageCount': 2}
    },
    'publishedFileCount': len(published),
    'files': published
}
save_json(ROOT / 'build-verification.json', report)
print(json.dumps(report['records'], ensure_ascii=False))
