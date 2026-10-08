from PIL import Image, ImageDraw, ImageFont
import pytesseract
from pathlib import Path

# Create a simple test image
img_dir = Path("storage/test_docs")
img_dir.mkdir(parents=True, exist_ok=True)
img_path = img_dir / "ocr_test.png"

img = Image.new("RGB", (300, 100), color=(255, 255, 255))
d = ImageDraw.Draw(img)
d.text((10, 30), "Tathya 41.6 Lakh", fill=(0, 0, 0))
img.save(img_path)

print("=== OCR READINESS TEST ===")
try:
    text = pytesseract.image_to_string(str(img_path), lang="eng").strip()
    if text:
        print(f"OCR_ENGLISH: PASS (Extracted: '{text}')")
    else:
        print("OCR_ENGLISH: FAIL (Empty extraction)")
except pytesseract.TesseractNotFoundError:
    print("OCR_ENGLISH: BLOCKED (Tesseract binary not installed on system PATH)")
except Exception as e:
    print(f"OCR_ENGLISH: FAIL ({e})")

try:
    langs = pytesseract.get_languages()
    if "hin" in langs:
        print("OCR_HINDI: PASS (Hindi traineddata found)")
    else:
        print("OCR_HINDI: NOT_READY (Hindi traineddata not installed, English available)")
except Exception:
    print("OCR_HINDI: NOT_READY (Tesseract binary not installed)")
