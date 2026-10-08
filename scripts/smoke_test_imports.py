import sys

print(f"Python interpreter: {sys.executable}")
print(f"Python version: {sys.version}")

try:
    import markitdown
    print("[PASS] markitdown")
except Exception as e:
    print(f"[FAIL] markitdown: {e}")

try:
    import pdfplumber
    print("[PASS] pdfplumber")
except Exception as e:
    print(f"[FAIL] pdfplumber: {e}")

try:
    import openpyxl
    print("[PASS] openpyxl")
except Exception as e:
    print(f"[FAIL] openpyxl: {e}")

try:
    import docx
    print("[PASS] python-docx")
except Exception as e:
    print(f"[FAIL] python-docx: {e}")

try:
    import numpy as np
    print(f"[PASS] numpy {np.__version__}")
except Exception as e:
    print(f"[FAIL] numpy: {e}")

try:
    import sentence_transformers
    print(f"[PASS] sentence_transformers {sentence_transformers.__version__}")
except Exception as e:
    print(f"[FAIL] sentence_transformers: {e}")

try:
    import transformers
    print(f"[PASS] transformers {transformers.__version__}")
except Exception as e:
    print(f"[FAIL] transformers: {e}")

try:
    import torch
    print(f"[PASS] torch {torch.__version__}")
    cuda_avail = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_avail}")
    if cuda_avail:
        print(f"GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"Device Count: {torch.cuda.device_count()}")
except Exception as e:
    print(f"[FAIL] torch: {e}")

try:
    import rank_bm25
    print("[PASS] rank_bm25")
except Exception as e:
    print(f"[FAIL] rank_bm25: {e}")

try:
    import presidio_analyzer
    print("[PASS] presidio_analyzer")
except Exception as e:
    print(f"[FAIL] presidio_analyzer: {e}")

try:
    import rapidfuzz
    print("[PASS] rapidfuzz")
except Exception as e:
    print(f"[FAIL] rapidfuzz: {e}")

try:
    import dateparser
    print("[PASS] dateparser")
except Exception as e:
    print(f"[FAIL] dateparser: {e}")

try:
    import z3
    print(f"[PASS] z3-solver {z3.__version__}")
except Exception as e:
    print(f"[FAIL] z3-solver: {e}")

try:
    import cryptography
    print(f"[PASS] cryptography {cryptography.__version__}")
except Exception as e:
    print(f"[FAIL] cryptography: {e}")

try:
    import qrcode
    print("[PASS] qrcode")
except Exception as e:
    print(f"[FAIL] qrcode: {e}")

try:
    import openai
    print(f"[PASS] openai {openai.__version__}")
except Exception as e:
    print(f"[FAIL] openai: {e}")

try:
    import google.genai
    print("[PASS] google.genai")
except Exception as e:
    print(f"[FAIL] google.genai: {e}")

try:
    import pytesseract
    print(f"[PASS] pytesseract {pytesseract.__version__}")
except Exception as e:
    print(f"[FAIL] pytesseract: {e}")

try:
    from PIL import Image
    print(f"[PASS] PIL/Pillow {Image.__version__}")
except Exception as e:
    print(f"[FAIL] PIL: {e}")

try:
    import fastapi
    print(f"[PASS] fastapi {fastapi.__version__}")
except Exception as e:
    print(f"[FAIL] fastapi: {e}")

try:
    import sqlmodel
    print(f"[PASS] sqlmodel {sqlmodel.__version__}")
except Exception as e:
    print(f"[FAIL] sqlmodel: {e}")

print("=== ALL IMPORT CHECKS COMPLETED ===")
