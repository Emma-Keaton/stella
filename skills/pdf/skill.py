from __future__ import annotations

import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

FEATURE_METADATA = {
    "name": "pdf",
    "aliases": ["pdf", "pdf tool", "pdf processor", "pdf extractor", "pdf merger", "pdf splitter"],
    "description": (
        "Read, extract, create, edit, and manipulate PDF files. "
        "Extract text/tables/images, merge/split/rotate, fill forms, "
        "OCR scanned PDFs, add watermarks, encrypt/decrypt."
    ),
    "triggers": [
        "pdf", "read pdf", "extract pdf", "create pdf", "merge pdf",
        "split pdf", "rotate pdf", "pdf form", "fill pdf", "ocr pdf",
        "watermark pdf", "encrypt pdf", "pdf to text", "pdf to images",
        "pdf metadata"
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "enum": [
                    "read_pdf", "extract_text", "extract_tables", "extract_images",
                    "extract_metadata", "create_pdf", "merge_pdfs", "split_pdf",
                    "rotate_pages", "add_watermark", "fill_form", "encrypt_pdf",
                    "decrypt_pdf", "ocr_pdf", "pdf_to_images", "images_to_pdf"
                ],
                "description": "The operation to perform"
            },
            "file_path": {"type": "STRING", "description": "Path to input PDF file"},
            "file_paths": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Array of PDF file paths for merge/split"},
            "output_path": {"type": "STRING", "description": "Output file path"},
            "pages": {"type": "STRING", "description": "Page range (e.g., '1-5', '1,3,5', 'all')"},
            "rotation": {"type": "NUMBER", "enum": [90, 180, 270], "description": "Rotation angle in degrees"},
            "watermark_text": {"type": "STRING", "description": "Text for watermark"},
            "watermark_opacity": {"type": "NUMBER", "minimum": 0, "maximum": 1, "default": 0.3, "description": "Watermark opacity"},
            "form_fields": {"type": "OBJECT", "description": "Form field values to fill"},
            "password": {"type": "STRING", "description": "Password for encryption/decryption"},
            "dpi": {"type": "INTEGER", "default": 150, "description": "DPI for PDF to images conversion"}
        },
        "required": ["operation"]
    },
    "version": "1.0.0",
    "active": True,
    "optional_dependencies": ["pypdf", "pdfplumber", "pdf-lib", "tesseract", "poppler"],
}

API_SOURCES = {
    "pypdf": {"name": "pypdf", "description": "Pure Python PDF library", "url": "https://pypdf.readthedocs.io", "auth_tier": "local"},
    "pdfplumber": {"name": "pdfplumber", "description": "Extract text and tables from PDFs", "url": "https://github.com/jsvine/pdfplumber", "auth_tier": "local"},
    "tesseract": {"name": "Tesseract OCR", "description": "OCR engine for scanned PDFs", "url": "https://tesseract-ocr.github.io", "auth_tier": "local"},
    "poppler": {"name": "Poppler", "description": "PDF utilities (pdftotext, pdfimages)", "url": "https://poppler.freedesktop.org", "auth_tier": "local"},
}

# Check available libraries
def _check_libs() -> Dict[str, bool]:
    libs = {}
    for lib in ["pypdf", "pdfplumber", "fitz", "PIL"]:
        try:
            __import__(lib)
            libs[lib] = True
        except ImportError:
            libs[lib] = False
    return libs

_LIBS = _check_libs()

def _op_result(title: str, summary: str, ok: bool, operation: str, data: Dict = None, narrative: str = None) -> Dict:
    return {
        "title": title,
        "summary": summary[:200],
        "spoken_narrative": narrative or summary[:200],
        "ok": ok,
        "operation": operation,
        "record": {"ok": ok, "content": summary, "data": data or {}},
    }

def _resolve_path(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p