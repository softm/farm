"""Check deployed bytes, desktop/mobile rendering and image dialog interaction."""
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://softm.github.io/farm/'
expected = json.loads((ROOT / 'build-verification.json').read_text())
results = {'sourceIntegrityComplete': expected['sourceIntegrityComplete'],
           'missingFiles': expected['missingFiles'], 'http': [], 'browser': []}
failed = []
for entry in expected['files']:
    url = BASE + urllib.parse.quote(entry['path'], safe='/')
    last_error = ''
    for attempt in range(12):
        try:
            req = urllib.request.Request(url + '?archive-check=' + str(time.time_ns()),
                headers={'User-Agent': 'farm-archive-verifier', 'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                status = response.status
            if hashlib.sha256(content).hexdigest() != entry['sha256']:
                raise ValueError('Published SHA-256 mismatch')
            results['http'].append({'path': entry['path'], 'status': status, 'sha256Match': True})
            break
        except Exception as error:
            last_error = str(error)
            time.sleep(5)
    else:
        failed.append({'path': entry['path'], 'error': last_error})
if failed:
    results['errors'] = failed
    (ROOT / 'live-verification.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    raise SystemExit('HTTP checks failed: ' + str(failed))

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width, height in [(1440,1000),(390,844)]:
        page = browser.new_page(viewport={'width':width,'height':height}, device_scale_factor=1)
        errors=[]
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE, wait_until='networkidle')
        page.wait_for_selector('.record')
        page.locator('#q').fill('존재하지않는검색어')
        assert not page.locator('.record').is_visible(), 'Search filtering failed'
        page.locator('#q').fill('박')
        assert page.locator('.record').is_visible(), 'Search restoration failed'
        page.goto(BASE+'records/20261009-bak-cultivation/',wait_until='networkidle')
        images=page.locator('img.zoomable')
        assert images.count()==5, 'Expected 4 diagrams and 1 photo or labeled preview'
        for index in range(images.count()):
            assert images.nth(index).evaluate('(e)=>e.complete&&e.naturalWidth>0'), 'Image did not load'
            images.nth(index).click()
            assert page.locator('#lightbox').evaluate('(e)=>e.open'), 'Dialog did not open'
            page.wait_for_function("(()=>{const e=document.getElementById('lightboxImg');return e.complete&&e.naturalWidth>0})()")
            page.keyboard.press('Escape')
        images.nth(0).click()
        first=page.locator('#lightboxImg').get_attribute('src')
        page.locator('#img-next').click()
        assert page.locator('#lightboxImg').get_attribute('src')!=first, 'Next image failed'
        page.locator('#img-prev').click()
        assert page.locator('#lightboxImg').get_attribute('src')==first, 'Previous image failed'
        page.keyboard.press('Escape')
        overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth+2')
        assert not overflow, 'Horizontal viewport overflow'
        assert not errors, 'JavaScript errors: '+str(errors)
        page.screenshot(path=str(ROOT/f'verified-{width}.png'),full_page=True)
        results['browser'].append({'viewport':[width,height],'loadedImages':5,
            'dialogOpenClose':True,'previousNext':True,'search':True,'horizontalOverflow':False})
        page.close()
    browser.close()
(ROOT/'live-verification.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'publicSiteVerified':True,'sourceIntegrityComplete':results['sourceIntegrityComplete'],
    'missingFiles':results['missingFiles'],'httpFileCount':len(results['http'])},ensure_ascii=False))
