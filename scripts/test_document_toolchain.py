import sys
from pathlib import Path

test_dir = Path("storage/test_docs")
test_dir.mkdir(parents=True, exist_ok=True)

# 1. TXT & MD
txt_file = test_dir / "sample.txt"
txt_file.write_text("Tathya fact checking plain text verification.", encoding="utf-8")
assert txt_file.read_text(encoding="utf-8") == "Tathya fact checking plain text verification."
print("TXT: PASS")

md_file = test_dir / "sample.md"
md_file.write_text("# Tathya Title\n\n- Fact 1: Value is INR 41.6L\n- Fact 2: Date is 22 Dec", encoding="utf-8")
assert "Fact 1: Value is INR 41.6L" in md_file.read_text(encoding="utf-8")
print("MD: PASS")

# 2. DOCX via python-docx
try:
    import docx
    doc_path = test_dir / "sample.docx"
    doc = docx.Document()
    doc.add_heading("Procurement Agreement", 0)
    doc.add_paragraph("Approved contract value is ₹41.6 lakh.")
    doc.save(doc_path)

    # Read back
    read_doc = docx.Document(doc_path)
    paragraphs = [p.text for p in read_doc.paragraphs]
    full_text = " ".join(paragraphs)
    assert "₹41.6 lakh" in full_text
    print("DOCX (python-docx): PASS")
except Exception as e:
    print(f"DOCX: FAIL ({e})")

# 3. XLSX via openpyxl
try:
    import openpyxl
    xlsx_path = test_dir / "sample.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Financials"
    ws.append(["Item", "Amount", "Status"])
    ws.append(["Contract Base", 4160000, "Approved"])
    wb.save(xlsx_path)

    # Read back
    wb_read = openpyxl.load_workbook(xlsx_path)
    sheet = wb_read["Financials"]
    val = sheet.cell(row=2, column=2).value
    assert val == 4160000
    print("XLSX (openpyxl): PASS")
except Exception as e:
    print(f"XLSX: FAIL ({e})")

# 4. PDF via pdfplumber
try:
    import pdfplumber
    import pypdfium2
    
    # We can create a minimal valid PDF using reportlab or pypdfium2 or minimal PDF bytes
    # Let's create a minimal valid PDF syntax
    pdf_path = test_dir / "sample.pdf"
    
    # Minimal 1-page PDF 1.4 stream
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n"
    )
    pdf_path.write_bytes(pdf_content)

    with pdfplumber.open(pdf_path) as pdf:
        num_pages = len(pdf.pages)
        assert num_pages == 1
    print("PDF (pdfplumber): PASS")
except Exception as e:
    print(f"PDF: FAIL ({e})")

# 5. MarkItDown fallback
try:
    from markitdown import MarkItDown
    md_converter = MarkItDown()
    result = md_converter.convert(str(txt_file))
    assert "Tathya fact checking" in result.text_content
    print("MarkItDown: PASS")
except Exception as e:
    print(f"MarkItDown: FAIL ({e})")

print("=== ALL DOCUMENT TOOLCHAIN TESTS COMPLETED ===")
