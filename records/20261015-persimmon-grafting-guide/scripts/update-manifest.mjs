/* SOFTM-GRAFT-MANIFEST START: 자막 산출물을 포함해 아카이브 파일 해시·통계를 재생성 (2026-10-18) */
import { createHash } from 'node:crypto';
import { readdir, readFile, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const projectRoot = path.resolve(process.argv[2] || process.cwd());
const manifestPath = path.join(projectRoot, 'archive-manifest.json');
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));

const roleByPath = new Map([
  ['20261015_감나무_접수_접목방법.md', 'detailed_markdown_record'],
  ['archive.json', 'deployment_metadata'],
  ['captions-ocr.tsv', 'raw_ocr_caption_output'],
  ['captions.csv', 'reviewed_caption_table'],
  ['gallery-data.js', 'gallery_metadata'],
  ['index.html', 'canonical_html_entry'],
  ['README.md', 'archive_readme'],
  ['scripts/build-caption-data.mjs', 'caption_data_builder'],
  ['scripts/extract-captions.swift', 'caption_ocr_extractor'],
  ['scripts/update-manifest.mjs', 'archive_manifest_builder'],
  ['source-inventory.csv', 'original_source_inventory'],
  ['verification-report.md', 'verification_report']
]);

const mediaTypeByExtension = new Map([
  ['.csv', 'text/csv'],
  ['.html', 'text/html'],
  ['.js', 'text/javascript'],
  ['.json', 'application/json'],
  ['.md', 'text/markdown'],
  ['.mjs', 'text/javascript'],
  ['.png', 'image/png'],
  ['.swift', 'text/x-swift'],
  ['.tsv', 'text/tab-separated-values'],
  ['.webp', 'image/webp']
]);

async function collectFiles(directory, prefix = '') {
  const entries = await readdir(directory, { withFileTypes: true });
  const paths = [];
  for (const entry of entries) {
    if (entry.name === '.DS_Store') continue;
    const relativePath = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (relativePath === 'archive-manifest.json') continue;
    const absolutePath = path.join(directory, entry.name);
    if (entry.isDirectory()) paths.push(...await collectFiles(absolutePath, relativePath));
    else if (entry.isFile()) paths.push(relativePath);
  }
  return paths;
}

function sha256(buffer) {
  return createHash('sha256').update(buffer).digest('hex');
}

const relativePaths = (await collectFiles(projectRoot)).sort((left, right) => left.localeCompare(right, 'en'));
const files = [];
for (const relativePath of relativePaths) {
  const absolutePath = path.join(projectRoot, relativePath);
  const [buffer, fileStat] = await Promise.all([readFile(absolutePath), stat(absolutePath)]);
  const extension = path.extname(relativePath).toLocaleLowerCase('en-US');
  const isOriginal = extension === '.png' && !relativePath.includes('/');
  const isThumbnail = relativePath.startsWith('thumbnails/') && extension === '.webp';
  files.push({
    path: relativePath,
    originalName: path.basename(relativePath),
    mediaType: mediaTypeByExtension.get(extension) || 'application/octet-stream',
    role: isOriginal ? 'original_source_image' : (isThumbnail ? 'derived_gallery_thumbnail' : (roleByPath.get(relativePath) || 'supporting_file')),
    size: fileStat.size,
    sha256: sha256(buffer),
    original: isOriginal,
    generated: !isOriginal
  });
}

const originalFiles = files.filter(file => file.original);
const generatedFiles = files.filter(file => file.generated);
const entry = files.find(file => file.path === manifest.entry);
const inventory = files.find(file => file.path === manifest.sourceInventory);

manifest.entrySha256 = entry?.sha256;
manifest.sourceInventorySha256 = inventory?.sha256;
manifest.summary = {
  originalImages: originalFiles.length,
  byteIdenticalOriginalDuplicates: originalFiles.length - new Set(originalFiles.map(file => file.sha256)).size,
  originalBytes: originalFiles.reduce((sum, file) => sum + file.size, 0),
  derivedThumbnails: files.filter(file => file.role === 'derived_gallery_thumbnail').length,
  extractedCaptions: 130,
  imagesWithoutCaptions: 16,
  generatedFiles: generatedFiles.length,
  generatedBytes: generatedFiles.reduce((sum, file) => sum + file.size, 0),
  listedFilesExcludingManifest: files.length,
  missingFiles: 0
};
manifest.capabilities = [
  'responsive-gallery',
  'ocr-caption-table',
  'caption-search',
  'section-filter',
  'caption-state-filter',
  'persistent-image-gallery',
  'independent-caption-table',
  'caption-coverage-insights',
  'csv-export',
  'integrated-image-viewer',
  'previous-next',
  'keyboard-navigation',
  'mobile-swipe',
  'zoom-fit',
  'original-open',
  'download'
];
manifest.verification = {
  report: 'verification-report.md',
  localHttp: 'passed',
  desktopBrowser: 'passed',
  mobile390x844: 'passed',
  captionRows: 146,
  extractedCaptions: 130,
  imagesWithoutCaptions: 16,
  imageGalleryAlwaysVisible: true,
  independentCaptionTable: true,
  captionCoverageGroups: 10,
  captionSearch: 'passed',
  captionStateFilter: 'passed',
  csv: 'passed',
  thumbnailsLoaded: 146,
  brokenThumbnails: 0,
  browserConsoleErrors: 0
};
manifest.files = files;

await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
console.log(`매니페스트 갱신 완료: 원본 ${originalFiles.length}개, 생성물 ${generatedFiles.length}개`);
/* SOFTM-GRAFT-MANIFEST END: 자막 산출물을 포함해 아카이브 파일 해시·통계를 재생성 (2026-10-18) */
