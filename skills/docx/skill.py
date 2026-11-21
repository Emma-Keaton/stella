from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

FEATURE_METADATA = {
    "name": "docx",
    "aliases": ["docx", "word", "word doc", "word document", ".docx", ".dotx"],
    "description": (
        "Create, read, edit, and manipulate Word documents (.docx, .dotx). "
        "Professional formatting: tables of contents, headings, page numbers, "
        "letterheads, tracked changes, comments, find-and-replace."
    ),
    "triggers": [
        "docx", "word doc", "word document", ".docx", ".dotx",
        "create document", "edit document", "report", "memo", "letter", "template",
        "table of contents", "tracked changes", "find and replace"
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "enum": ["create_docx","read_docx","replace_text","add_toc","convert_to_pdf","merge_docx"]},
            "file_path": {"type": "STRING", "description": "Path to input DOCX file"},
            "file_paths": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Array of DOCX file paths"},
            "output_path": {"type": "STRING", "description": "Output file path"},
            "content": {"type": "STRING", "description": "Content for new document"},
            "find": {"type": "STRING", "description": "Text to find"},
            "replace": {"type": "STRING", "description": "Text to replace with"},
        },
        "required": ["operation"]
    },
    "version": "1.0.0",
    "active": True,
    "optional_dependencies": ["python-docx", "pandoc", "libreoffice"],
}

API_SOURCES = {
    "python-docx": {"name": "python-docx", "description": "Create and update Word documents", "url": "https://python-docx.readthedocs.io", "auth_tier": "local"},
    "pandoc": {"name": "pandoc", "description": "Universal document converter", "url": "https://pandoc.org", "auth_tier": "local"},
    "libreoffice": {"name": "LibreOffice", "description": "Office suite for conversion", "url": "https://libreoffice.org", "auth_tier": "local"},
}

# Check available libraries
def _check_libs() -> Dict[str, bool]:
    libs = {}
    for lib in ["docx", "pandoc"]:
        try:
            if lib == "docx":
                import docx
            else:
                subprocess.run([lib, "--version"], capture_output=True)
            libs[lib] = True
        except (ImportError, FileNotFoundError):
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
def _op_create_docx(kwargs: dict) -> dict:
    output_path = kwargs.get("output_path")
    content = kwargs.get("content", "")
    if not output_path:
        return _op_result("DOCX", "No output_path provided", False, "create_docx")
    
    out_path = _resolve_path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if _LIBS.get("docx"):
            from docx import Document
            from docx.shared import Inches, Pt, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            
            doc = Document()
            title = doc.add_heading('Stella Document', level=0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            if content:
                for line in content.split('\n'):
                    if line.strip():
                        doc.add_paragraph(line)
            
            doc.add_heading('Table of Contents', level=1)
            doc.add_paragraph('Right-click and select "Update Field" to generate TOC')
            
            doc.save(str(out_path))
            return _op_result("DOCX", f"Created document at {out_path}", True, "create_docx", {"output_path": str(out_path)}, f"Created DOCX at {out_path.name}")
        else:
            import zipfile
            with zipfile.ZipFile(out_path, 'w') as z:
                z.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')
                z.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')
                z.writestr('word/_rels/document.xml.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>''')
                doc_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>Stella Document</w:t></w:r></w:p><w:p><w:r><w:t>{content.replace(chr(10), '</w:t></w:r></w:p><w:p><w:r><w:t>') if content else ''}</w:t></w:r></w:p></w:body>
</w:document>'''
                z.writestr('word/document.xml', doc_xml)
            
            return _op_result("DOCX", f"Created minimal DOCX at {out_path}", True, "create_docx", {"output_path": str(out_path)}, f"Created DOCX at {out_path.name} (install python-docx for full features)")
    except Exception as e:
        return _op_result("DOCX", f"Creation failed: {e}", False, "create_docx")
def _op_read_docx(kwargs: dict) -> dict:
    file_path = kwargs.get("file_path")
    if not file_path:
        return _op_result("DOCX", "No file_path provided", False, "read_docx")
    
    path = _resolve_path(file_path)
    if not path.exists():
        return _op_result("DOCX", f"File not found: {file_path}", False, "read_docx")
    
    try:
        if _LIBS.get("docx"):
            from docx import Document
            doc = Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            tables = []
            for table in doc.tables:
                table_data = [[cell.text for cell in row.cells] for row in table.rows]
                tables.append(table_data)
            return _op_result("DOCX", f"Read {len(paragraphs)} paragraphs, {len(tables)} tables", True, "read_docx", 
                            {"paragraphs": paragraphs, "tables": tables}, 
                            f"Document has {len(paragraphs)} paragraphs and {len(tables)} tables")
        else:
            result = subprocess.run(["pandoc", "-t", "markdown", str(path)], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return _op_result("DOCX", "Read via pandoc", True, "read_docx", 
                                {"markdown": result.stdout}, 
                                f"Read document via pandoc: {len(result.stdout)} chars")
            return _op_result("DOCX", "Install python-docx or pandoc for reading", False, "read_docx")
    except Exception as e:
        return _op_result("DOCX", f"Read failed: {e}", False, "read_docx")

def _op_replace_text(kwargs: dict) -> dict:
    file_path = kwargs.get("file_path")
    output_path = kwargs.get("output_path")
    find = kwargs.get("find")
    replace = kwargs.get("replace")
    if not all([file_path, output_path, find, replace]):
        return _op_result("DOCX", "file_path, output_path, find, and replace required", False, "replace_text")
    
    path = _resolve_path(file_path)
    out_path = _resolve_path(output_path)
    
    try:
        if _LIBS.get("docx"):
            from docx import Document
            doc = Document(str(path))
            count = 0
            for paragraph in doc.paragraphs:
                if find in paragraph.text:
                    for run in paragraph.runs:
                        if find in run.text:
                            run.text = run.text.replace(find, replace)
                            count += 1
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if find in paragraph.text:
                                for run in paragraph.runs:
                                    if find in run.text:
                                        run.text = run.text.replace(find, replace)
                                        count += 1
            doc.save(str(out_path))
            return _op_result("DOCX", f"Replaced {count} occurrences", True, "replace_text", 
                            {"output_path": str(out_path), "replacements": count}, 
                            f"Replaced '{find}' with '{replace}' {count} times in {path.name}")
        else:
            return _op_result("DOCX", "Install python-docx for replace_text", False, "replace_text")
    except Exception as e:
        return _op_result("DOCX", f"Replace failed: {e}", False, "replace_text")
def _op_add_toc(kwargs: dict) -> dict:
    file_path = kwargs.get("file_path")
    output_path = kwargs.get("output_path")
    if not file_path or not output_path:
        return _op_result("DOCX", "file_path and output_path required", False, "add_toc")
    
    path = _resolve_path(file_path)
    out_path = _resolve_path(output_path)
    
    try:
        if _LIBS.get("docx"):
            from docx import Document
            from docx.oxml.ns import qn
            from docx.oxml import OxmlElement
            
            doc = Document(str(path))
            
            p = doc.paragraphs[0].insert_paragraph_before('Table of Contents')
            p.style = 'Heading 1'
            
            run = p.add_run()
            fldChar = OxmlElement('w:fldChar')
            fldChar.set(qn('w:fldCharType'), 'begin')
            run._r.append(fldChar)
            
            run2 = p.add_run()
            instrText = OxmlElement('w:instrText')
            instrText.set(qn('xml:space'), 'preserve')
            instrText.text = ' TOC \\o "1-3" \\h \\z \\u '
            run2._r.append(instrText)
            
            run3 = p.add_run()
            fldChar2 = OxmlElement('w:fldChar')
            fldChar2.set(qn('w:fldCharType'), 'end')
            run3._r.append(fldChar2)
            
            doc.save(str(out_path))
            return _op_result("DOCX", "Added Table of Contents field", True, "add_toc", 
                            {"output_path": str(out_path)}, 
                            f"Added TOC field to {path.name}. Right-click and select 'Update Field' in Word to generate.")
        else:
            return _op_result("DOCX", "Install python-docx for add_toc", False, "add_toc")
    except Exception as e:
        return _op_result("DOCX", f"Add TOC failed: {e}", False, "add_toc")

def _op_convert_to_pdf(kwargs: dict) -> dict:
    file_path = kwargs.get("file_path")
    output_path = kwargs.get("output_path")
    if not file_path or not output_path:
        return _op_result("DOCX", "file_path and output_path required", False, "convert_to_pdf")
    
    path = _resolve_path(file_path)
    out_path = _resolve_path(output_path)
    
    try:
        result = subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_path.parent), str(path)], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return _op_result("DOCX", f"Converted to PDF", True, "convert_to_pdf", 
                            {"output_path": str(out_path)}, 
                            f"Converted {path.name} to PDF at {out_path.name}")
        
        result = subprocess.run(["pandoc", str(path), "-o", str(out_path)], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return _op_result("DOCX", f"Converted to PDF via pandoc", True, "convert_to_pdf", 
                            {"output_path": str(out_path)}, 
                            f"Converted {path.name} to PDF at {out_path.name}")
        
        return _op_result("DOCX", "Need libreoffice or pandoc for PDF conversion", False, "convert_to_pdf")
    except Exception as e:
        return _op_result("DOCX", f"Conversion failed: {e}", False, "convert_to_pdf")

def _op_merge_docx(kwargs: dict) -> dict:
    file_paths = kwargs.get("file_paths", [])
    output_path = kwargs.get("output_path")
    if len(file_paths) < 2:
        return _op_result("DOCX", "Need at least 2 DOCX files", False, "merge_docx")
    if not output_path:
        return _op_result("DOCX", "output_path required", False, "merge_docx")
    
    return _op_result("DOCX", "DOCX merge requires python-docx with manual XML concatenation. Use python-docx to append content from each file.", False, "merge_docx")

_OPERATIONS = {
    "create_docx": _op_create_docx,
    "read_docx": _op_read_docx,
    "replace_text": _op_replace_text,
    "add_toc": _op_add_toc,
    "convert_to_pdf": _op_convert_to_pdf,
    "merge_docx": _op_merge_docx,
}

def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "DOCX",
            "summary": f"Unknown operation '{operation}'. Available: {', '.join(sorted(_OPERATIONS))}",
            "spoken_narrative": f"Unknown DOCX operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        return handler(kwargs)
    except Exception as exc:
        return {
            "title": "DOCX",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"DOCX error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }