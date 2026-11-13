TAMIL BOOK OF ENOCH — AUDIOBOOK KIT

Voice: ta-IN-ValluvarNeural (Tamil male voice)
Style: Natural Tamil narration, slightly slower and lower-pitched
Output: Individual section MP3 files + one complete MP3

IMPORTANT
The PDF is image-based/scanned and uses a 2-column layout.
The script processes the pages column-by-column to preserve correct reading order
and recognizes Tamil text using Tesseract OCR.
Internet access is required for Microsoft Edge Text-to-Speech.

WINDOWS SETUP
1. Install Python 3.10+.
2. Ensure Tesseract OCR for Windows is installed (with Tamil tam.traineddata).
   The script auto-detects Tesseract in standard locations (C:\Python\Tesseract-OCR, etc.).
3. (Optional) Install FFmpeg and add to PATH (if absent, script uses direct binary MP3 merging).
4. In your terminal, run:

   pip install -r requirements.txt

5. Put the PDF in this folder, then run:

   python create_audiobook.py "Tamil - Book of Enoch by R.H. Charles.pdf"

OUTPUT
The script creates Book_of_Enoch_Tamil_Audiobook\ containing:
- Book_of_Enoch_Tamil_OCR.txt (Extracted Tamil text in exact reading order)
- One MP3 per detected section/chapter
- Book_of_Enoch_Tamil_Complete.mp3
