"""Verify live GitHub Pages bytes, record links, responsive rendering, and media viewers."""
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://softm.github.io/farm/'
expected = json.loads((ROOT / 'build-verification.json').read_text(encoding='utf-8'))
results = {'records': expected['records'], 'http': [], 'browser': [], 'sprinklerVerified': False}
failed = []

for entry in expected['files']:
    url = BASE + urllib.parse.quote(entry['path'], safe='/')
    last_error = ''
    for attempt in range(12):
        try:
            req = urllib.request.Request(
                url + '?archive-check=' + str(time.time_ns()),
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
    (ROOT / 'live-verification.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    raise SystemExit('HTTP checks failed: ' + str(failed))

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width, height in [(1440,1000),(390,844)]:
        page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))

        # Project home must render both canonical records from archive-index.json.
        page.goto(BASE, wait_until='networkidle')
        page.wait_for_selector('.record')
        page.wait_for_function("document.body.innerText.includes('스프링클러 배관 나사 규격 정리')")
        assert page.locator('.record').count() == 3, 'Expected three farm public records'
        page.locator('#q').fill('스프링클러')
        assert page.locator('.record').count() == 1
        visible = page.locator('.record:visible')
        assert visible.count() == 1 and '스프링클러 배관 나사 규격 정리' in visible.first.inner_text()
        page.locator('#q').fill('')

        # Existing Bak image dialog remains healthy.
        page.goto(BASE + 'records/20261009-bak-cultivation/', wait_until='networkidle')
        images = page.locator('img.zoomable')
        assert images.count() == 5, 'Expected 4 diagrams and 1 photo/preview'
        for index in range(images.count()):
            assert images.nth(index).evaluate('(e)=>e.complete&&e.naturalWidth>0'), 'Bak image did not load'

        # Completed sprinkler record: all three attachment files load and integrated viewer works.
        page.goto(BASE + 'records/20261009-sprinkler-thread-guide/', wait_until='networkidle')
        assert page.locator('h1').first.inner_text().strip() == '스프링클러 배관 나사 규격 정리'
        media = page.locator('img.media')
        assert media.count() == 3, 'Expected three preserved sprinkler attachment files'
        for index in range(media.count()):
            assert media.nth(index).evaluate('(e)=>e.complete&&e.naturalWidth>0'), 'Sprinkler image did not load'
        media.nth(0).click()
        assert page.locator('#viewer').evaluate("(e)=>getComputedStyle(e).display==='flex'"), 'Viewer did not open'
        first = page.locator('#viewerImg').get_attribute('src')
        page.locator('#next').click()
        assert page.locator('#viewerImg').get_attribute('src') != first, 'Next image failed'
        page.locator('#prev').click()
        assert page.locator('#viewerImg').get_attribute('src') == first, 'Previous image failed'
        page.keyboard.press('ArrowRight')
        assert page.locator('#viewerImg').get_attribute('src') != first, 'Keyboard next failed'
        page.keyboard.press('Escape')
        assert page.locator('#viewer').evaluate("(e)=>getComputedStyle(e).display==='none'"), 'Viewer close failed'

        overflow = page.evaluate('document.documentElement.scrollWidth>innerWidth+2')
        assert not overflow, 'Horizontal viewport overflow'
        assert not errors, 'JavaScript errors: ' + str(errors)
        page.screenshot(path=str(ROOT / f'verified-{width}.png'), full_page=True)
        results['browser'].append({
            'viewport': [width,height],
            'farmRecordCount': 3,
            'sprinklerImages': 3,
            'viewerPreviousNext': True,
            'viewerKeyboard': True,
            'viewerClose': True,
            'horizontalOverflow': False
        })
        page.close()
    browser.close()

results['sprinklerVerified'] = all(
    x.get('sourceIntegrityComplete') for x in [results['records']['20261009-sprinkler-thread-guide']]
)
(ROOT / 'live-verification.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({
    'publicSiteVerified': True,
    'sprinklerVerified': results['sprinklerVerified'],
    'httpFileCount': len(results['http'])
}, ensure_ascii=False))
