#!/usr/bin/env python3
"""Create a Tamil Book of Enoch audiobook from a scanned PDF.
Uses column-segmented Tesseract OCR (with Tamil data), FFmpeg (optional), and Edge TTS.
"""
from pathlib import Path
import re, sys, asyncio, subprocess, shutil, io
import pymupdf as fitz
import pytesseract
from PIL import Image, ImageOps
import edge_tts

# Auto-detect Tesseract executable if not found in PATH
if shutil.which('tesseract') is None:
    for candidate in [
        r'C:\Python\Tesseract-OCR\tesseract.exe',
        Path.home() / r'AppData\Local\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]:
        if Path(candidate).is_file():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            break

PDF = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('Tamil - Book of Enoch by R.H. Charles.pdf')
OUT = Path('Book_of_Enoch_Tamil_Audiobook')
VOICE = 'ta-IN-ValluvarNeural'  # Tamil male voice
RATE = '-8%'
PITCH = '-4Hz'
MAX_CHARS = 2600


def clean_tamil_text(text: str) -> str:
    # Strip zero-width formatting characters that confuse TTS
    text = text.replace('\u200c', '').replace('\u200b', '').replace('\x0c', ' ')
    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove recurring running headers and page numbers
    text = re.sub(r'(?m)^\s*ஏனோக்க[னன்]?\s*புத்தகம்\s*$', '', text)
    text = re.sub(r'(?m)^\s*\d+\s*$', '', text)
    # Common OCR glyph corrections for Tamil fonts
    text = text.replace('ஆ€ர்வாதத்', 'ஆசீர்வாதத்').replace('ஆச€ீர்வ', 'ஆசீர்வ').replace('€னாய்', 'சீனாய்').replace('பூமயி', 'பூமி')
    text = re.sub(r'நீ(?:துி?|இ)மான்', 'நீதிமான்', text)
    text = re.sub(r'நீ(?:துி?|இ)மான்க', 'நீதிமான்க', text)
    text = re.sub(r'ஆச[€ீ]+ர்வ[இி]ு?த்', 'ஆசீர்வதித்', text)
    text = re.sub(r'ஆசர்வ[இி]ு?க்க', 'ஆசீர்வதிக்க', text)
    text = re.sub(r'ஆ[€ீ]+ர்வாதத்', 'ஆசீர்வாதத்', text)
    text = re.sub(r'மி[இி]த்து', 'மிதித்து', text)
    text = re.sub(r'வருஒறார்', 'வருகிறார்', text)
    text = re.sub(r'ப்படு[இி]ன்ற', 'ப்படுகின்றன', text)
    return text.strip()


def ocr_column(page, clip_rect) -> str:
    pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), clip=clip_rect, alpha=False)
    image = Image.open(io.BytesIO(pix.tobytes('png'))).convert('L')
    image = ImageOps.autocontrast(image)
    raw = pytesseract.image_to_string(image, lang='tam+eng', config='--psm 6')
    return clean_tamil_text(raw)


def ocr_pdf(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc, 1):
        w, h = page.rect.width, page.rect.height
        
        # On Page 1, start the left column below the cover illustration (y >= 380)
        y_top_left = 380 if i == 1 else 48
        y_top_right = 48
        y_bottom = h - 50

        col_left = fitz.Rect(25, y_top_left, w / 2, y_bottom)
        col_right = fitz.Rect(w / 2, y_top_right, w - 25, y_bottom)

        left_text = ocr_column(page, col_left)
        right_text = ocr_column(page, col_right)

        page_combined = '\n\n'.join(t for t in (left_text, right_text) if t)
        pages.append(f'\n\n{page_combined}')
        print(f'OCR page {i}/{len(doc)}', flush=True)

    full_text = '\n\n'.join(pages)
    return clean_tamil_text(full_text)


def split_chapters(text: str):
    # Matches both அதிகாரம் and அத்தியாயம் (Chapters 1 & 2 use அத்தியாயம், others use அதிகாரம்)
    pattern = re.compile(r'(?m)^\s*(?:அதிகாரம்|அத்தியாயம்)\s*[:.-]?\s*([0-9௦-௯]+|[a-zA-Z\u0B80-\u0BFF]+)?\s*$', re.UNICODE)
    matches = list(pattern.finditer(text))
    if not matches:
        print('WARNING: No reliable chapter headings detected; using one full-book track.')
        return [('முழு புத்தகம்', text)]
    chapters = []
    if matches[0].start() > 0:
        front = text[:matches[0].start()].strip()
        if len(front) > 150:
            chapters.append(('முன்னுரை', front))
    for i, match in enumerate(matches):
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        raw_num = match.group(1) or str(i + 1)
        body = text[match.start():end].strip()
        chapters.append((f'அதிகாரம்_{raw_num}', body))
    return chapters


def chunk_text(text: str, limit=MAX_CHARS):
    paras = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    chunks, cur = [], ''
    for para in paras:
        while len(para) > limit:
            cut = para.rfind('。', 0, limit)
            if cut < limit // 2: cut = para.rfind('.', 0, limit)
            if cut < limit // 2: cut = limit
            piece, para = para[:cut+1], para[cut+1:]
            if cur: chunks.append(cur); cur = ''
            chunks.append(piece.strip())
        candidate = (cur + '\n\n' + para).strip()
        if len(candidate) > limit and cur:
            chunks.append(cur); cur = para
        else:
            cur = candidate
    if cur: chunks.append(cur)
    return chunks


async def make_mp3(text: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    await communicate.save(str(dest))


def concat_mp3(files, dest: Path):
    if shutil.which('ffmpeg'):
        listing = dest.with_suffix('.txt')
        listing.write_text(''.join("file '" + str(p.resolve()).replace("'", "'\\''") + "'\n" for p in files), encoding='utf-8')
        subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(listing), '-c:a', 'libmp3lame', '-q:a', '3', str(dest)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        listing.unlink(missing_ok=True)
    else:
        # Fallback binary concatenation for MP3 audio streams
        with open(dest, 'wb') as outfile:
            for f in files:
                with open(f, 'rb') as infile:
                    shutil.copyfileobj(infile, outfile)


async def main():
    if not PDF.exists():
        raise SystemExit(f'PDF not found: {PDF.resolve()}\nPut the PDF beside this script or pass its path.')
    OUT.mkdir(exist_ok=True)
    text = ocr_pdf(PDF)
    (OUT / 'Book_of_Enoch_Tamil_OCR.txt').write_text(text, encoding='utf-8')
    chapters = split_chapters(text)
    print(f'Detected {len(chapters)} sections. Review the OCR text and headings before relying on the audio.')
    chapter_mp3s = []
    for idx, (title, body) in enumerate(chapters, 1):
        safe = re.sub(r'[^\w஀-௿-]+', '_', title).strip('_') or f'Chapter_{idx:02d}'
        pieces = []
        for part_no, chunk in enumerate(chunk_text(body), 1):
            part = OUT / 'parts' / f'{idx:02d}_{part_no:03d}.mp3'
            print(f'Synthesizing {title}, part {part_no}', flush=True)
            await make_mp3(chunk, part)
            pieces.append(part)
        chapter_file = OUT / f'{idx:02d}_{safe}.mp3'
        if len(pieces) == 1:
            shutil.copy2(pieces[0], chapter_file)
        else:
            concat_mp3(pieces, chapter_file)
        chapter_mp3s.append(chapter_file)
    concat_mp3(chapter_mp3s, OUT / 'Book_of_Enoch_Tamil_Complete.mp3')
    print('\nDONE:', OUT.resolve())
    print('Check the OCR text and chapter boundaries: scan quality can cause Tamil OCR errors.')

if __name__ == '__main__':
    asyncio.run(main())
