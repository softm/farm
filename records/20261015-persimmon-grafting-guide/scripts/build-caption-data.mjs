/* SOFTM-GRAFT-CAPTION-DATA START: OCR 결과를 교정해 갤러리 자막과 CSV 표를 생성 (2026-10-18) */
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const projectRoot = path.resolve(process.argv[2] || process.cwd());
const galleryPath = path.join(projectRoot, 'gallery-data.js');
const ocrPath = path.join(projectRoot, 'captions-ocr.tsv');
const csvPath = path.join(projectRoot, 'captions.csv');

const gallerySource = await readFile(galleryPath, 'utf8');
const arrayStart = gallerySource.indexOf('[');
const arrayEnd = gallerySource.lastIndexOf('];');
if (arrayStart < 0 || arrayEnd < arrayStart) {
  throw new Error('gallery-data.js에서 이미지 배열을 찾지 못했습니다.');
}

const items = JSON.parse(gallerySource.slice(arrayStart, arrayEnd + 1));
const ocrRows = (await readFile(ocrPath, 'utf8'))
  .trimEnd()
  .split(/\r?\n/)
  .slice(1)
  .map(line => {
    const [sequence, file, ...captionParts] = line.split('\t');
    return [sequence, { file, subtitle: captionParts.join('\t').trim() }];
  });
const ocrBySequence = new Map(ocrRows);

const reviewedCorrections = {
  '007': '금년도 4월까지 안전하게 보관을 할 수 있다 이렇게 말씀드릴 수 있겠습니다.',
  '010': '아직 물이 오르지 않았기 때문에 이때 접수를 채취해야 되지 3월이 넘어서 채취하게 되면',
  '063': '내가 필요로 할 때 언제든지 이만한 양을 녹여서 접수를 만들 때에',
  '064': '도포제로 활용을 할 수 있다. 이렇게 말씀을 드리겠습니다. 자 이것도 귀찮아서 싫다.',
  '081': '그 다음에 아까 말씀드린 도포제 그리고 접수를 자를 수 있는 전정가위 또 이렇게',
  '084': '대목을 전정가위로 자르기 어려울 때 쓸 수 있는 톱이 필요합니다.',
  '103': '삐진 다음에 아까 2.5cm 정도 된다고 했죠 그러면 눈이 있는 쪽으로 해서 반듯이 날립니다.',
  '104': '삐진 다음에 아까 2.5cm 정도 된다고 했죠 그러면 눈이 있는 쪽으로 해서 반듯이 날립니다.',
  '125': '한 3cm 정도 내렸습니다. 그래서 접수도 조금 굵은 것으로 제가 선택을 했습니다.',
  '145': '가지 같은 것을 이용해서 이렇게 고라니 같은 것들이 접목한 것을 치지 않도록'
};

const normalizedItems = items.map(item => {
  const ocr = ocrBySequence.get(item.sequence);
  if (!ocr || ocr.file !== item.file) {
    throw new Error(`${item.sequence}번 OCR 결과와 갤러리 파일이 일치하지 않습니다.`);
  }

  const subtitle = reviewedCorrections[item.sequence] ?? ocr.subtitle;
  return {
    sequence: item.sequence,
    file: item.file,
    thumbnail: item.thumbnail,
    group: item.group,
    caption: item.caption,
    subtitle,
    keywords: item.keywords
  };
});

if (normalizedItems.length !== 146) {
  throw new Error(`이미지 수가 146장이 아닙니다: ${normalizedItems.length}`);
}

const galleryOutput = `/** SOFTM-GRAFT-GALLERY START: 원본 146장 정렬·구간·설명·OCR 자막 데이터 생성 (2026-10-15, 자막 보강 2026-10-18) */\nwindow.GRAFT_ARCHIVE_ITEMS = ${JSON.stringify(normalizedItems, null, 2)};\n/** SOFTM-GRAFT-GALLERY END: 원본 146장 정렬·구간·설명·OCR 자막 데이터 생성 (2026-10-15, 자막 보강 2026-10-18) */\n`;
await writeFile(galleryPath, galleryOutput, 'utf8');

const csvCell = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
const csvRows = [
  ['번호', '구간', '자막 여부', '추출 자막', '파일명'],
  ...normalizedItems.map(item => [
    item.sequence,
    item.group,
    item.subtitle ? '있음' : '없음',
    item.subtitle,
    item.file
  ])
];
const csvOutput = `\ufeff${csvRows.map(row => row.map(csvCell).join(',')).join('\n')}\n`;
await writeFile(csvPath, csvOutput, 'utf8');

const withSubtitle = normalizedItems.filter(item => item.subtitle).length;
const withoutSubtitle = normalizedItems.length - withSubtitle;
console.log(`자막 데이터 생성 완료: 있음 ${withSubtitle}장, 없음 ${withoutSubtitle}장`);
/* SOFTM-GRAFT-CAPTION-DATA END: OCR 결과를 교정해 갤러리 자막과 CSV 표를 생성 (2026-10-18) */
