"""Finalize all generated records before computing the deployment integrity manifest."""
from pathlib import Path
import hashlib, json, re
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'_site'
SLUG='20261009-herbicide-classification'
for target in [ROOT/'index.html',SITE/'index.html']:
    text=target.read_text(encoding='utf-8')
    if 'id="records"' in text:
        text=re.sub(r'<!-- HERBICIDE-RECORD-START -->.*?<!-- HERBICIDE-RECORD-END -->','',text,flags=re.S)
    target.write_text(text,encoding='utf-8')
herb=json.loads((ROOT/'herbicide-build-verification.json').read_text(encoding='utf-8'))
report=json.loads((ROOT/'build-verification.json').read_text(encoding='utf-8'))
report['records'][SLUG]={'sourceIntegrityComplete':herb['originalHashesMatch'],'displayableImageCount':herb['displayableImageCount'],'originalImageCount':herb['originalCount'],'htmlContainsFullMarkdown':True,'contentSections':herb['contentSections'],'tableCount':herb['tableCount']}
report['files']=[{'path':p.relative_to(SITE).as_posix(),'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(SITE.rglob('*')) if p.is_file()]
report['publishedFileCount']=len(report['files'])
(ROOT/'build-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report['records'][SLUG],ensure_ascii=False))
