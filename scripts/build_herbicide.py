#!/usr/bin/env python3
"""Build the comprehensive farm herbicide archive, without replacing other records.
Run after build_archive.py in Pages; --folder PATH --standalone builds an offline copy.
"""
from pathlib import Path
import argparse, base64, csv, hashlib, html, io, json, re, shutil, zipfile
from datetime import datetime, timezone
from markdown_it import MarkdownIt

ROOT=Path(__file__).resolve().parents[1]
SLUG='20261009-herbicide-classification'
BASE='https://softm.github.io/farm/'
TITLE='제초제 분류와 제품 비교 — 대화 전체 재정리'
INPUT_ZIP='herbicide-guide-20261009.zip'
p=argparse.ArgumentParser();p.add_argument('--folder');p.add_argument('--standalone',action='store_true');args=p.parse_args()
D=Path(args.folder).resolve() if args.folder else ROOT/'records'/SLUG
D.mkdir(parents=True,exist_ok=True)
def write(name,text): (D/name).write_text(text,encoding='utf-8')
def dump(name,value): write(name,json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def sha(data): return hashlib.sha256(data).hexdigest()
def esc(value): return html.escape(str(value),quote=True)

md=(D/'README.md').read_text(encoding='utf-8')
patch_file=D/'fact-patches.json'
if patch_file.exists():
    for patch in json.loads(patch_file.read_text(encoding='utf-8')): md=md.replace(patch['old'],patch['new'])
write('README.md',md)
assert '30% + 2%' not in md, 'Uncorrected DANGOL concentration'
assert '들깨(씨)와 콩' in md, 'Current manufacturer crop/placement qualification missing'
assert len(md.encode('utf-8'))>14000 and md.count('### Q')>=6, 'Do not deploy the old abbreviated guide'

# An optional, explicitly derivative atlas is only a byte-transport format for web copies.
# It must never be represented as the nine original JPEG files.
atlas_dir=D/'web-transport'
if (atlas_dir/'atlas.json').exists():
    from PIL import Image
    spec=json.loads((atlas_dir/'atlas.json').read_text(encoding='utf-8'))
    encoded=''.join((atlas_dir/name).read_text(encoding='ascii') for name in spec['parts'])
    data=base64.b64decode(re.sub(r'\s+','',encoded),validate=True)
    assert sha(data)==spec['atlasSha256'],'Atlas transport hash mismatch'
    atlas=Image.open(io.BytesIO(data)).convert('RGB')
    (D/'previews').mkdir(exist_ok=True)
    for item in spec['images']:
        x,y,w,h=item['rect'];image=atlas.crop((x,y,x+w,y+h))
        image.save(D/'previews'/(Path(item['name']).stem+'.webp'),'WEBP',lossless=True,method=4)

media=json.loads((D/'media.json').read_text(encoding='utf-8'))
for item in media:
    original=D/'images'/item['name'];preview=D/'previews'/(Path(item['name']).stem+'.webp')
    item['originalAvailable']=original.exists() and sha(original.read_bytes())==item['sha256']
    if original.exists() and not item['originalAvailable']: raise ValueError('Original hash mismatch: '+item['name'])
    if item['originalAvailable']:
        item.update(src='images/'+item['name'],variant='original',servedSha256=item['sha256'])
    elif preview.exists():
        item.update(src='previews/'+preview.name,variant='preview',servedSha256=sha(preview.read_bytes()))
    else: item.update(src=None,variant='missing',servedSha256=None)
originals=sum(x['originalAvailable'] for x in media)
visible=sum(bool(x['src']) for x in media)
previews=sum(x['variant']=='preview' for x in media)
complete=originals==len(media)==9
now=datetime.now(timezone.utc).isoformat()

rows=[['確認項目','記入欄','確認方法']]
rows=[['확인 항목','기입란','확인 방법'],['상표','','병의 정확한 제품명'],['성분·함량·제형','','보유 제품 라벨'],['등록번호','','보유 제품 라벨'],['작물·수확 용도','','씨/잎 등 정확한 등록명'],['잡초·생육단계','','등록 잡초 및 엽기'],['사용 시기·처리 부위','','토양/경엽/휴간 등 같은 적용 행'],['물 20L당 약량','','적용 행 확인 후 기록'],['면적당 약량·물량','','1,000㎡ 기준 등'],['수확 전 제한·횟수','','안전사용기준'],['피복·시설·토양 제한','','약효·약해 주의사항'],['참고한 라벨·조회 날짜','','사진이나 조회 결과 보존'],['확인 결과','','미확인 항목이 있으면 임의 처방하지 않음']]
with (D/'사용전_확인표.csv').open('w',encoding='utf-8-sig',newline='') as f: csv.writer(f).writerows(rows)

manifest={'schemaVersion':1,'project':'농업·농사','repository':'softm/farm','slug':SLUG,'inputZipName':INPUT_ZIP,'title':TITLE,'generatedAt':now,'expectedOriginalCount':9,'originalCount':originals,'webDerivativeCount':previews,'displayableImageCount':visible,'originalBytesComplete':complete,'images':media,'privacy':{'originalJPEGs':'Unmodified originals belong in the user-delivered source ZIP. Public derivatives, when present, are separately identified.','webDerivativesAreOriginals':False}}
dump('manifest.json',manifest)

renderer=MarkdownIt('commonmark',{'html':True}).enable('table')
body=renderer.render(md)
toc=[];number=0
def heading(match):
    global number
    number+=1;level=match.group(1);inside=match.group(2);ident='section-'+str(number)
    if level=='2': toc.append((ident,re.sub('<[^>]+>','',inside)))
    return '<h'+level+' id="'+ident+'">'+inside+'</h'+level+'>'
body=re.sub(r'<h([23])>(.*?)</h\1>',heading,body,flags=re.S)
body=re.sub(r'<table>(.*?)</table>',r'<div class="table-wrap" tabindex="0" role="region" aria-label="가로로 스크롤할 수 있는 표"><table>\1</table></div>',body,flags=re.S)
gallery=[]
for product in dict.fromkeys(item['product'] for item in media):
    cards=[]
    for i,item in enumerate(media):
        if item['product']!=product:continue
        visual='<img src="'+esc(item['src'])+'" alt="'+esc(item['product']+' '+item['caption'])+'" loading="lazy">' if item['src'] else '<span class="placeholder">웹 파일 없음<br>원본은 전체 ZIP 보존</span>'
        variant='원본 JPG' if item['variant']=='original' else '공개 열람용 변환본' if item['variant']=='preview' else '웹 원본 미확보'
        cards.append('<button type="button" class="media-card" data-media="'+str(i)+'" aria-label="사진 '+str(i+1)+' '+esc(item['product']+' '+item['caption'])+' 열기">'+visual+'<span class="number">사진 '+str(i+1)+' / 9</span><span class="caption">'+esc(item['caption'])+'</span><span class="filename">'+esc(item['name'])+'</span><span class="variant">'+variant+'</span></button>')
    gallery.append('<section class="media-group"><h3>'+esc(product)+'</h3><div class="media-grid">'+''.join(cards)+'</div></section>')
zip_name=INPUT_ZIP if complete else 'herbicide-guide-20261009-web.zip'
zip_label='전체 ZIP · 원본 JPG 9장 포함' if complete else '웹 열람본 ZIP · 원본 JPG와 별도'
if complete: status='원본 JPG 9장의 SHA-256이 제공 파일과 일치합니다. 이미지의 크기·내용·파일명을 바꾸지 않았습니다.'
elif visible==9: status='사진 9장을 공개 열람용 변환본으로 표시합니다. 원본 JPG와 파일 형식·해시는 다릅니다. 공개본에 가린 연락처 등은 원본 ZIP에만 보존합니다. 원본 JPG 9장 포함 ZIP은 대화 첨부로 별도 제공합니다.'
else: status=f'원본 JPG {originals}/9장, 공개 열람 가능한 이미지 {visible}/9장입니다. 없는 파일을 표시·업로드 완료로 계산하지 않습니다.'
appendix=(D/'대화_흐름과_요구사항.md').read_text(encoding='utf-8') if (D/'대화_흐름과_요구사항.md').exists() else ''
appendix_html=renderer.render(appendix)
meta_json=json.dumps(media,ensure_ascii=False).replace('</','<\\/')
nav=''.join('<a href="#'+ident+'">'+esc(title)+'</a>' for ident,title in toc)
page='''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><meta name="description" content="풀앤짱·푸리타·스톰프·라쏘·단골·케이펜디의 분류, 사용자 질문 전체, 라벨 해석과 오류 정정, 사진 9장."><link rel="canonical" href="'''+BASE+'records/'+SLUG+'''/"><title>'''+esc(TITLE)+''' · 농업·농사</title><link rel="stylesheet" href="reader.css"><script src="viewer.js" defer></script></head><body><header class="masthead"><nav class="top-links" aria-label="프로젝트 이동"><a href="https://softm.github.io/projects/">전체 프로젝트</a><a href="https://softm.github.io/projects/farm/">농업·농사 프로젝트</a><a href="../../">농업 아카이브</a></nav><p class="eyebrow">AGRICULTURE / HERBICIDE FIELD NOTES</p><h1>제초제 분류와 제품 비교<br>대화 전체 재정리</h1><p>제품 이름만 나열한 기록에서 벗어나, 무엇을 확인했고 무엇을 정정했는지 함께 읽는 제초제 아카이브입니다.</p><div class="chips"><span>6종 비교</span><span>사진 9개 항목</span><span>6개 질문·논점</span><span>등록·처방과 구분</span></div></header><div class="shell"><aside class="toc"><strong>목차</strong><a href="#photos">제품 사진 9장</a>'''+nav+'''<a href="#conversation">대화 흐름·요구사항</a><a href="#files">파일·검증 정보</a></aside><main class="content"><div class="status'''+('' if complete else ' pending')+'">'+esc(status)+'''</div><div class="download-bar"><a href="'''+zip_name+'">'+zip_label+'''</a><a href="README.md" download>상세 Markdown</a><a href="사용전_확인표.csv" download>사용 전 확인표 CSV</a><a href="#photos">사진 뷰어</a></div><section id="photos"><h2>제품 사진 — 같은 제품끼리 묶어 보기</h2><p class="footnote">사진을 누르면 이전·다음으로 9장을 연속해서 볼 수 있습니다. ← → 이동 · ESC 닫기 · + − 확대/축소 · 0 화면 맞춤. 모바일에서는 화면 맞춤 상태에서 좌우로 넘깁니다.</p>'''+''.join(gallery)+'''</section>'''+body+'''<section id="conversation"><h2>대화 흐름과 요구사항</h2><details class="appendix"><summary>사진 제공부터 최종 재정리 요청까지 전체 논점 열기</summary>'''+appendix_html+'''</details><p><a href="대화_흐름과_요구사항.md" download>대화 흐름 Markdown 저장</a></p></section><section id="files"><h2>파일·검증 정보</h2><p>본문 내용의 사실 확인과 실제 웹 배포 검증은 구분합니다. 원본과 변환본의 해시는 manifest에서 별도로 확인할 수 있습니다.</p><div class="download-bar"><a href="manifest.json">파일 manifest</a><a href="SHA256SUMS.txt">SHA-256 목록</a><a href="verification.json">빌드 검증 결과</a></div><details class="appendix"><summary>현재 포함 파일과 미디어 상태</summary><pre>'''+esc(json.dumps({'원본_JPG':originals,'웹_변환본':previews,'열람_이미지':visible,'원본_바이트_완비':complete},ensure_ascii=False,indent=2))+'''</pre></details></section></main></div><dialog id="media-viewer" class="viewer" aria-label="제품 사진 통합 뷰어"><div class="viewer-inner"><div class="viewer-nav"><button type="button" id="viewer-prev">← 이전</button><span id="viewer-count" class="counter" aria-live="polite">1 / 9</span><button type="button" id="viewer-next">다음 →</button><button type="button" id="viewer-close">닫기 ✕</button></div><div class="viewer-tools"><button id="viewer-minus" type="button" aria-label="축소">−</button><button id="viewer-plus" type="button" aria-label="확대">+</button><button id="viewer-fit" type="button">화면 맞춤</button><span id="viewer-zoom">화면 맞춤</span><a id="viewer-original" target="_blank" rel="noopener" hidden>원본 열기</a><a id="viewer-download" download hidden>저장</a></div><div class="stage"><img id="viewer-image" alt="제품 사진 확대" hidden><p id="viewer-error" class="image-error" hidden></p></div><div class="viewer-info"><div id="viewer-caption"></div><div id="viewer-filename" class="file"></div></div></div></dialog><script type="application/json" id="media-data">'''+meta_json+'''</script><footer>농업·농사 · softm/farm · 원본 기록 주소 유지 · 실제 사용은 정확한 제품 라벨과 공식 등록사항으로 확인합니다.</footer></body></html>'''
write('index.html',page)
report={'schemaVersion':1,'generatedAt':now,'contentCharacters':len(md),'contentSections':len(toc),'tableCount':body.count('<table>'),'questionCount':6,'expectedMediaCount':9,'originalCount':originals,'displayableImageCount':visible,'mediaPathsExist':all(not x['src'] or (D/x['src']).is_file() for x in media),'originalHashesMatch':complete,'allNineImagesDisplayable':visible==9,'javascriptIncluded':(D/'viewer.js').exists(),'stylesIncluded':(D/'reader.css').exists(),'liveBrowserVerified':False,'note':'This report is a build result, not a substitute for live-verification.json.'}
dump('verification.json',report)
files=[]
for f in sorted(D.rglob('*')):
    if f.is_file() and f.suffix!='.zip' and 'web-transport' not in f.parts and f.name not in {'SHA256SUMS.txt'}: files.append(f)
write('SHA256SUMS.txt',''.join(sha(f.read_bytes())+'  '+f.relative_to(D).as_posix()+'\n' for f in files))
with zipfile.ZipFile(D/zip_name,'w',zipfile.ZIP_DEFLATED) as z:
    for f in sorted(D.rglob('*')):
        if f.is_file() and f.suffix!='.zip' and 'web-transport' not in f.parts: z.write(f,SLUG+'/'+f.relative_to(D).as_posix())
with zipfile.ZipFile(D/zip_name) as z: assert z.testzip() is None

if not args.standalone:
    index_path=ROOT/'archive-index.json';index=json.loads(index_path.read_text(encoding='utf-8'))
    record={'id':SLUG,'slug':SLUG,'listTitle':INPUT_ZIP,'sourceTitle':TITLE,'title':TITLE,'titleSource':'user-override','inputName':INPUT_ZIP,'inputKind':'zip','date':'2026-10-09','dateBasis':'archive_created','eventDate':None,'kind':'방제 · 농약 관리','visibility':'public','url':BASE+'records/'+SLUG+'/','repoUrl':'https://github.com/softm/farm/tree/main/records/'+SLUG,'originalPhotoCount':originals,'expectedOriginalPhotoCount':9,'previewCount':previews,'displayableImageCount':visible,'sourceIntegrityComplete':complete,'publicMediaComplete':visible==9,'originalsDelivery':'source ZIP attached to user conversation' if not complete else 'repository and source ZIP','sourceFileCount':len(files)+2,'summary':'6종 비교·분류 체계·질문 전체·라벨 단위·오류 정정·출처·사진 9개 항목. '+('원본 9장 보존.' if complete else '공개 열람본과 원본 ZIP을 구분.'),'files':{'images':visible,'videos':0,'audio':0,'documents':4}}
    index['records']=[record]+[r for r in index.get('records',[]) if r.get('slug')!=SLUG]
    index['updatedAt']=now;index_path.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    site=ROOT/'_site';site.mkdir(exist_ok=True)
    shutil.copy2(index_path,site/'archive-index.json')
    destination=site/'records'/SLUG
    if destination.exists():shutil.rmtree(destination)
    shutil.copytree(D,destination,ignore=shutil.ignore_patterns('web-transport','fact-patches.json'))
    home=ROOT/'index.html';home_text=home.read_text(encoding='utf-8')
    marker='<!-- HERBICIDE-RECORD-START -->';end='<!-- HERBICIDE-RECORD-END -->'
    card=marker+'<article id="herbicide-feature" class="record"><p class="meta">2026-10-09 · 방제 · 농약 관리</p><h2><a href="records/'+SLUG+'/">'+INPUT_ZIP+'</a></h2><p>'+esc(TITLE)+'</p><p>제품 6종 · 사진 9개 항목 · 전체 Q&A · 오류 정정 · 상세 근거</p></article>'+end
    if marker in home_text:home_text=re.sub(re.escape(marker)+r'.*?'+re.escape(end),card,home_text,flags=re.S)
    else:home_text=home_text.replace('</main>',card+'</main>')
    home.write_text(home_text,encoding='utf-8');(site/'index.html').write_text(home_text,encoding='utf-8')
    (ROOT/'herbicide-build-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
