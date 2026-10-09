#!/usr/bin/env python3
"""Recover only the nine already-authorized herbicide photos, by exact SHA-256.
Reads existing PUBLIC repositories belonging to softm; never substitutes previews,
never scans private repositories, and never changes or deletes source files.
"""
from pathlib import Path
import concurrent.futures, hashlib, io, json, os, re, time, urllib.parse, urllib.request, zipfile
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'records/20261009-herbicide-classification/images'
EXPECTED = {
 '1000056270.jpg':'a6158e2688120f0ac77767631cc078d6c6ecbe248d83a58eee8b45a25d5c9ed04',
 '1000056271.jpg':'fe5f4f6d82c05be608bebe7d583e17fbea553f057e8e27072bc2946d5ee6be5b20',
 '1000056272.jpg':'cbbd8e82d5c418f57e4a536518277231aac5d00d98d8cbe64b3a3c2e6c92b42be7',
 '1000056273.jpg':'3e014e7282f98517c0c1f5413f6b233a5b0d8d99599326e6b41502bb0518eb58cb',
 '1000056274.jpg':'34e3364de1dfa61b8a263439d85d9d163f0dc4df06ace0f96a3ca098cff18a52c2',
 '1000056275.jpg':'342123a795a78f51ce5b82c2f5e7d1f2abfd1473a88b5b576af553d77fd4a5c9',
 '1000056243.jpg':'f137b3a3385680f9e06fcb7ae8d921a1fbdfc18e4ade4f139ef73baf0abaa31a10',
 '1000056244.jpg':'2d8a7d198e72a91e840a7a711bc2245003299eefc52c5c3f12733ffb943eb84e41',
 '1000056245.jpg':'df3d9a772cab345c1ea3a664a591bea76e3bada92e72e00a2cc920560d0e3667a0'
}
GIT_BLOBS = {'ce8eaab9e3a0265075068508f0126ab3d0fde260','b21df8e1056c5913a5783b531065932460d8e8d97','69be06b03535764db357d2ed661c26380fdf2644','1283244724764c044999a3c50099a4a77c6c102a','c899620940d2a728e496582517b5d82c0993f4a7b5','3791b601986b5b683d99e8476b0eae00747980b1d','58b26fadb71cdc9e7971fc5d7c1b953f0633dfdf','3c859f36d36a7eef1fef197bb6ce802719580d8f','fe4f848aa1ac3c9edfa1088f91edf351746ec315'}
BY_HASH = {h:n for n,h in EXPECTED.items()}
report = {'expectedOriginalCount':9, 'matches':[], 'scannedArchives':[], 'errors':[]}
DEST.mkdir(parents=True, exist_ok=True)
def fetch(url, limit=150_000_000):
    headers={'User-Agent':'softm-farm-original-integrity-check'}
    if url.startswith('https://api.github.com/') and os.environ.get('GH_TOKEN'):
        headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=90) as r:
        if int(r.headers.get('Content-Length','0'))>limit: raise ValueError('size limit')
        data=r.read(limit+1)
    if len(data)>limit: raise ValueError('size limit')
    return data

def match(data,source):
    h=hashlib.sha256(data).hexdigest()
    if h in BY_HASH:
        name=BY_HASH[h]; (DEST/name).write_bytes(data)
        if not any(x['name']==name for x in report['matches']): report['matches'].append({'name':name,'sha256':h,'source':source,'bytes':len(data)})

def scan_zip(data,source,depth=0):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                if info.is_dir() or info.file_size>150_000_000: continue
                suffix=Path(info.filename).suffix.lower()
                if suffix in {'.jpg','.jpeg','.png','.webp'} and info.file_size<=2_000_000:
                    match(z.read(info),source+'!'+info.filename)
                elif suffix=='.zip' and depth<2:
                    scan_zip(z.read(info),source+'!'+info.filename,depth+1)
    except (zipfile.BadZipFile,RuntimeError,ValueError) as e:
        report['errors'].append({'source':source,'error':str(e)})

for name in EXPECTED:
    p=DEST/name
    if p.exists(): match(p.read_bytes(),'existing destination')
repos=['softm/farm','softm/hwagok-farm','softm/softm.github.io']
candidates=[]; seen=set()
for repo in repos:
    try:
        meta=json.loads(fetch('https://api.github.com/repos/'+repo,2_000_000))
        if meta.get('private'): raise ValueError('private source not permitted')
        branch=meta['default_branch']
        tree=json.loads(fetch('https://api.github.com/repos/'+repo+'/git/trees/'+urllib.parse.quote(branch,safe='')+'?recursive=1',25_000_000))
        for x in tree.get('tree',[]):
            if x.get('type')!='blob': continue
            path=x['path']; url='https://raw.githubusercontent.com/'+repo+'/'+branch+'/'+urllib.parse.quote(path,safe='/')
            if x.get('sha') in GIT_BLOBS:
                match(fetch(url,2_000_000),url)
            elif path.lower().endswith('.zip') and x.get('sha') not in seen and x.get('size',0)<=150_000_000:
                # Only the relevant herbicide/plant-protection archives and inbox bundles.
                if re.search(r'herbicide|제초|농약|풀앤|푸리타|농업.*zip|농장압축|inbox.*bundle|20260704',path,re.I):
                    seen.add(x['sha']); candidates.append((repo,path,url,x.get('size',0)))
    except Exception as e: report['errors'].append({'source':repo,'error':str(e)})
candidates.sort(key=lambda x:(0 if re.search(r'herbicide|제초|농약|풀앤|푸리타|20260704',x[1],re.I) else 1,x[3]))
budget=0
for repo,path,url,size in candidates:
    if len(report['matches'])==9: break
    if budget+size>650_000_000: continue
    budget+=size
    try:
        data=fetch(url); scan_zip(data,url)
        report['scannedArchives'].append({'repository':repo,'path':path,'bytes':len(data)})
    except Exception as e: report['errors'].append({'source':url,'error':str(e)})
report['foundOriginalCount']=len(report['matches'])
report['complete']=len(report['matches'])==9
report['missing']=[n for n,h in EXPECTED.items() if not (DEST/n).exists() or hashlib.sha256((DEST/n).read_bytes()).hexdigest()!=h]
(ROOT/'herbicide-original-recovery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
