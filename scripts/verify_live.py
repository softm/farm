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

        # Project home must render every public record from archive-index.json.
        page.goto(BASE, wait_until='networkidle')
        page.wait_for_selector('.record')
        page.wait_for_function("document.body.innerText.includes('스프링클러 배관 나사 규격 정리')")
        assert page.locator('.record').count() == 6, 'Expected five farm public records'  # SOFTM-farm-record-count: 감나무 기록을 포함한 공개 기록 수 검증 (2026-10-15)
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

        # SOFTM-persimmon-live-verification START: 감나무 기록 146장과 통합 뷰어를 실배포 환경에서 검증 (2026-10-15)
        page.goto(BASE + 'records/20261015-persimmon-grafting-guide/', wait_until='networkidle')
        assert page.locator('h1').first.inner_text().strip() == '2026-10-15 감나무 접수·접목 방법'
        # SOFTM-persimmon-caption-verification START: 상시 이미지 갤러리·독립 자막 표·구간 인사이트를 실배포에서 검증 (2026-10-18)
        cards = page.locator('#gallery-grid .gallery-card')
        assert page.locator('#gallery-grid').is_visible(), 'Persimmon image gallery must stay visible'
        assert cards.count() == 146, 'Expected 146 preserved persimmon source images'
        assert page.locator('#image-result-count').inner_text() == '146장'
        caption_rows = page.locator('#caption-table-body tr')
        assert caption_rows.count() == 146, 'Expected 146 persimmon caption table rows'
        assert page.locator('#caption-result-count').inner_text() == '146행 · 자막 130'
        assert page.locator('.coverage-card').count() == 10, 'Expected 10 caption coverage groups'
        assert page.locator('.insight-card strong').all_inner_texts() == ['146', '130', '16', '10']
        assert page.locator('.caption-table th').all_inner_texts() == ['번호', '작업 구간', '추출 자막', '화면 설명', '원본']

        page.locator('#image-search').fill('고라니')
        assert page.locator('#image-result-count').inner_text() == '9장'
        assert cards.count() == 9, 'Expected 9 gallery search results'
        assert caption_rows.count() == 146, 'Gallery search must not alter caption table'
        page.locator('#image-search').fill('')

        page.locator('#caption-search').fill('고라니')
        assert page.locator('#caption-result-count').inner_text() == '9행 · 자막 9'
        assert caption_rows.count() == 9, 'Expected 9 caption search results'
        assert cards.count() == 146, 'Caption search must not alter image gallery'
        page.locator('#caption-search').fill('')

        page.locator('#caption-filter').select_option('without')
        assert page.locator('#caption-result-count').inner_text() == '16행 · 자막 0'
        assert caption_rows.count() == 16, 'Expected 16 images without captions'
        assert cards.count() == 146, 'Caption status filter must not alter image gallery'
        page.locator('#caption-filter').select_option('all')

        simulation_coverage = page.locator('.coverage-card').filter(has_text='돌감나무 대목 시연')
        simulation_coverage.click()
        assert page.locator('#caption-group-filter').input_value() == '돌감나무 대목 시연'
        assert page.locator('#caption-result-count').inner_text() == '25행 · 자막 9'
        assert caption_rows.count() == 25, 'Expected 25 simulation coverage rows'
        simulation_coverage.click()
        assert page.locator('#caption-result-count').inner_text() == '146행 · 자막 130'
        # SOFTM-persimmon-caption-verification END: 상시 이미지 갤러리·독립 자막 표·구간 인사이트를 실배포에서 검증 (2026-10-18)
        thumbnails = page.locator('.gallery-card img')
        assert thumbnails.count() == 146, 'Expected 146 generated persimmon thumbnails'
        for index in [0, 72, 145]:
            thumbnail = thumbnails.nth(index)
            thumbnail.scroll_into_view_if_needed()
            handle = thumbnail.element_handle()
            assert handle is not None, 'Persimmon thumbnail element missing'
            page.wait_for_function('(e)=>e.complete&&e.naturalWidth>0', arg=handle, timeout=10000)
        cards.nth(0).click()
        assert page.locator('#viewer').evaluate('(e)=>e.open'), 'Persimmon viewer did not open'
        # SOFTM-persimmon-original-load START: 실제 원본 디코딩과 한글 NFC 경로를 첫째·셋째·마지막 이미지에서 검증 (2026-10-15)
        viewer_image = page.locator('#viewer-media img')
        first_handle = viewer_image.element_handle()
        assert first_handle is not None, 'Persimmon original element missing'
        page.wait_for_function('(e)=>e.complete&&e.naturalWidth>0', arg=first_handle, timeout=10000)
        first = viewer_image.get_attribute('src')
        page.locator('#viewer-next').click()
        assert viewer_image.get_attribute('src') != first, 'Persimmon next image failed'
        page.locator('#viewer-next').click()
        third_handle = viewer_image.element_handle()
        assert third_handle is not None, 'Persimmon third original element missing'
        page.wait_for_function('(e)=>e.complete&&e.naturalWidth>0', arg=third_handle, timeout=10000)
        assert page.locator('#viewer-counter').inner_text() == '3 / 146', 'Persimmon third original navigation failed'
        page.keyboard.press('Escape')
        assert not page.locator('#viewer').evaluate('(e)=>e.open'), 'Persimmon viewer close failed'
        cards.nth(145).click()
        last_handle = viewer_image.element_handle()
        assert last_handle is not None, 'Persimmon last original element missing'
        page.wait_for_function('(e)=>e.complete&&e.naturalWidth>0', arg=last_handle, timeout=10000)
        assert page.locator('#viewer-counter').inner_text() == '146 / 146', 'Persimmon last original navigation failed'
        page.keyboard.press('Escape')
        assert not page.locator('#viewer').evaluate('(e)=>e.open'), 'Persimmon last original close failed'
        # SOFTM-persimmon-original-load END: 실제 원본 디코딩과 한글 NFC 경로를 첫째·셋째·마지막 이미지에서 검증 (2026-10-15)
        # SOFTM-persimmon-live-verification END: 감나무 기록 146장과 통합 뷰어를 실배포 환경에서 검증 (2026-10-15)

        overflow = page.evaluate('document.documentElement.scrollWidth>innerWidth+2')
        assert not overflow, 'Horizontal viewport overflow'
        assert not errors, 'JavaScript errors: ' + str(errors)
        page.screenshot(path=str(ROOT / f'verified-{width}.png'), full_page=True)
        results['browser'].append({
            'viewport': [width,height],
            'farmRecordCount': 6,  # SOFTM-farm-record-count-result: 감나무 기록 포함 집계 저장 (2026-10-15)
            'sprinklerImages': 3,
            'persimmonImages': 146,  # SOFTM-persimmon-image-result: 감나무 원본 이미지 검증 수 저장 (2026-10-15)
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
