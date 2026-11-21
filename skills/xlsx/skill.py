from __future__ import annotations

import json
import subprocess
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

FEATURE_METADATA = {
    "name": "xlsx",
    "aliases": ["xlsx", "excel", "spreadsheet", ".xlsx", ".xlsm", ".xltx", ".csv", ".tsv"],
    "description": (
        "Create, read, edit, and analyze spreadsheets (.xlsx, .xlsm, .xltx, .csv, .tsv). "
        "Formulas, formatting, charts, data cleaning, financial models, data validation, pivot tables."
    ),
    "triggers": [
        "xlsx", "excel", "spreadsheet", ".xlsx", ".xlsm", ".csv", ".tsv",
        "create spreadsheet", "edit spreadsheet", "financial model", "formulas", "charts",
        "data cleaning", "pivot table", "data validation"
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "enum": ["create_xlsx","read_xlsx","read_csv","write_csv","add_formula","add_chart","clean_data","recalculate","convert_format"]},
            "file_path": {"type": "STRING", "description": "Path to input spreadsheet file"},
            "file_paths": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Array of file paths"},
            "output_path": {"type": "STRING", "description": "Output file path"},
            "sheet_name": {"type": "STRING", "description": "Sheet name"},
            "cell": {"type": "STRING", "description": "Cell reference (e.g., 'B10')"},
            "formula": {"type": "STRING", "description": "Formula string"},
            "data": {"type": "ARRAY", "items": {"type": "ARRAY", "items": {"type": "STRING"}}, "description": "Data as rows of strings"},
            "chart_type": {"type": "STRING", "enum": ["bar","line","pie","scatter","area"], "description": "Chart type"},
            "range": {"type": "STRING", "description": "Cell range (e.g., 'A1:B10')"},
            "validation_rule": {"type": "STRING", "description": "Data validation rule"}
        },
        "required": ["operation"]
    },
    "version": "1.0.0",
    "active": True,
    "optional_dependencies": ["openpyxl", "pandas", "libreoffice"],
}

API_SOURCES = {
    "openpyxl": {"name": "openpyxl", "description": "Read/write Excel 2010 xlsx/xlsm files", "url": "https://openpyxl.readthedocs.io", "auth_tier": "local"},
    "pandas": {"name": "pandas", "description": "Data analysis library with Excel support", "url": "https://pandas.pydata.org", "auth_tier": "local"},
    "libreoffice": {"name": "LibreOffice", "description": "Office suite for recalculation", "url": "https://libreoffice.org", "auth_tier": "local"},
}

# Check available libraries
def _check_libs() -> Dict[str, bool]:
    libs = {}
    for lib in ["openpyxl", "pandas"]:
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
def _op_create_xlsx(kwargs: dict) -> dict:
    output_path = kwargs.get("output_path")
    data = kwargs.get("data", [])
    if not output_path:
        return _op_result("XLSX", "No output_path provided", False, "create_xlsx")
    out_path = _resolve_path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if _LIBS.get("openpyxl"):
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment
            wb = Workbook()
            ws = wb.active
            ws.title = kwargs.get("sheet_name", "Sheet1")
            for row_idx, row in enumerate(data, 1):
                for col_idx, value in enumerate(row, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    if isinstance(value, str) and value.startswith("="):
                        cell.value = value
            if data:
                header_font = Font(bold=True)
                for cell in ws[1]:
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center")
            wb.save(str(out_path))
            return _op_result("XLSX", f"Created spreadsheet at {out_path}", True, "create_xlsx", {"output_path": str(out_path), "rows": len(data)}, f"Created XLSX with {len(data)} rows at {out_path.name}")
        else:
            with open(out_path.with_suffix('.csv'), 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(data)
            return _op_result("XLSX", f"Created CSV (openpyxl not installed)", True, "create_xlsx", {"output_path": str(out_path.with_suffix('.csv')), "rows": len(data)}, f"Created CSV at {out_path.with_suffix('.csv').name}. Install openpyxl for XLSX.")
    except Exception as e:
        return _op_result("XLSX", f"Creation failed: {e}", False, "create_xlsx")
    return p
def _op_read_xlsx(kwargs: dict) -> dict:
    file_path = kwargs.get("file_path")
    if not file_path:
        return _op_result("XLSX", "No file_path provided", False, "read_xlsx")
    path = _resolve_path(file_path)
    if not path.exists():
        return _op_result("XLSX", f"File not found: {file_path}", False, "read_xlsx")
    try:
        if _LIBS.get("openpyxl"):
            from openpyxl import load_workbook
            wb = load_workbook(str(path))
            sheets = {}
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = []
                for row in ws.iter_rows(values_only=True):
                    if any(v is not None for v in row):
                        rows.append(list(row))
                sheets[sheet_name] = rows
            return _op_result("XLSX", f"Read {len(sheets)} sheets", True, "read_xlsx", {"sheets": sheets}, f"Read {len(sheets)} sheets from {path.name}")
        elif _LIBS.get("pandas"):
            import pandas as pd
            sheets = pd.read_excel(str(path), sheet_name=None)
            result = {name: df.values.tolist() for name, df in sheets.items()}
            return _op_result("XLSX", f"Read {len(sheets)} sheets via pandas", True, "read_xlsx", {"sheets": result}, f"Read {len(sheets)} sheets from {path.name}")
        else:
            return _op_result("XLSX", "Install openpyxl or pandas for reading", False, "read_xlsx")
    except Exception as e:
        return _op_result("XLSX", f"Read failed: {e}", False, "read_xlsx")

def _op_read_csv(kwargs: dict) -> dict:
    file_path = kwargs.get("file_path")
    if not file_path:
        return _op_result("XLSX", "No file_path provided", False, "read_csv")
    path = _resolve_path(file_path)
    if not path.exists():
        return _op_result("XLSX", f"File not found: {file_path}", False, "read_csv")
    try:
        if _LIBS.get("pandas"):
            import pandas as pd
            df = pd.read_csv(str(path))
            return _op_result("XLSX", f"Read CSV: {len(df)} rows, {len(df.columns)} cols", True, "read_csv", 
                            {"data": df.values.tolist(), "columns": df.columns.tolist()}, 
                            f"Read CSV {path.name}: {len(df)} rows, {len(df.columns)} columns")
        else:
            with open(path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            return _op_result("XLSX", f"Read CSV: {len(rows)} rows", True, "read_csv", {"data": rows}, f"Read CSV {path.name}: {len(rows)} rows")
    except Exception as e:
        return _op_result("XLSX", f"CSV read failed: {e}", False, "read_csv")

def _op_add_formula(kwargs: dict) -> dict:
    file_path = kwargs.get("file_path")
    output_path = kwargs.get("output_path")
    cell = kwargs.get("cell")
    formula = kwargs.get("formula")
    if not all([file_path, output_path, cell, formula]):
        return _op_result("XLSX", "file_path, output_path, cell, and formula required", False, "add_formula")
    path = _resolve_path(file_path)
    out_path = _resolve_path(output_path)
    try:
        if _LIBS.get("openpyxl"):
            from openpyxl import load_workbook
            wb = load_workbook(str(path))
            ws = wb.active
            ws[cell] = formula
            wb.save(str(out_path))
            return _op_result("XLSX", f"Added formula to {cell}", True, "add_formula", 
                            {"output_path": str(out_path), "cell": cell, "formula": formula}, 
                            f"Added formula {formula} to cell {cell} in {path.name}")
        else:
            return _op_result("XLSX", "Install openpyxl for formulas", False, "add_formula")
    except Exception as e:
        return _op_result("XLSX", f"Formula add failed: {e}", False, "add_formula")

def _op_add_chart(kwargs: dict) -> dict:
    file_path = kwargs.get("file_path")
    output_path = kwargs.get("output_path")
    chart_type = kwargs.get("chart_type", "bar")
    data_range = kwargs.get("range", "A1:B10")
    if not all([file_path, output_path, chart_type, data_range]):
        return _op_result("XLSX", "file_path, output_path, chart_type, and range required", False, "add_chart")
def _op_clean_data(kwargs: dict) -> dict:
    file_path = kwargs.get("file_path")
    output_path = kwargs.get("output_path")
    if not file_path or not output_path:
        return _op_result("XLSX", "file_path and output_path required", False, "clean_data")
    path = _resolve_path(file_path)
    out_path = _resolve_path(output_path)
    try:
        if _LIBS.get("pandas"):
            import pandas as pd
            df = pd.read_excel(str(path)) if path.suffix in ['.xlsx', '.xlsm'] else pd.read_csv(str(path))
            df = df.dropna(how='all').dropna(axis=1, how='all')
            df = df.replace('', pd.NA)
            df.to_excel(str(out_path), index=False)
            return _op_result("XLSX", f"Cleaned data: {len(df)} rows, {len(df.columns)} cols", True, "clean_data", 
                            {"output_path": str(out_path), "rows": len(df), "cols": len(df.columns)}, 
                            f"Cleaned {path.name} -> {out_path.name}: {len(df)} rows, {len(df.columns)} columns")
        else:
            return _op_result("XLSX", "Install pandas for data cleaning", False, "clean_data")
    except Exception as e:
        return _op_result("XLSX", f"Clean failed: {e}", False, "clean_data")

def _op_recalculate(kwargs: dict) -> dict:
    file_path = kwargs.get("file_path")
    if not file_path:
        return _op_result("XLSX", "file_path required", False, "recalculate")
    path = _resolve_path(file_path)
    try:
        result = subprocess.run(["libreoffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(path.parent), str(path)], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return _op_result("XLSX", "Recalculated formulas", True, "recalculate", 
                            {"file_path": str(path)}, f"Recalculated formulas in {path.name} using LibreOffice")
        return _op_result("XLSX", "LibreOffice required for recalculation", False, "recalculate")
    except Exception as e:
        return _op_result("XLSX", f"Recalculation failed: {e}", False, "recalculate")

def _op_convert_format(kwargs: dict) -> dict:
    file_path = kwargs.get("file_path")
    output_path = kwargs.get("output_path")
    if not file_path or not output_path:
        return _op_result("XLSX", "file_path and output_path required", False, "convert_format")
    path = _resolve_path(file_path)
    out_path = _resolve_path(output_path)
    try:
        if _LIBS.get("pandas"):
            import pandas as pd
            df = pd.read_excel(str(path)) if path.suffix in ['.xlsx', '.xlsm'] else pd.read_csv(str(path))
            if out_path.suffix == '.csv':
                df.to_csv(str(out_path), index=False)
            elif out_path.suffix in ['.xlsx', '.xlsm']:
                df.to_excel(str(out_path), index=False)
            elif out_path.suffix == '.json':
                df.to_json(str(out_path), orient='records')
            else:
                df.to_excel(str(out_path), index=False)
            return _op_result("XLSX", f"Converted {path.suffix} -> {out_path.suffix}", True, "convert_format", 
                            {"output_path": str(out_path)}, f"Converted {path.name} to {out_path.name}")
        else:
            result = subprocess.run(["pandoc", str(path), "-o", str(out_path)], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return _op_result("XLSX", f"Converted via pandoc", True, "convert_format", 
                                {"output_path": str(out_path)}, f"Converted {path.name} to {out_path.name}")
            return _op_result("XLSX", "Install pandas or pandoc for conversion", False, "convert_format")
    except Exception as e:
        return _op_result("XLSX", f"Conversion failed: {e}", False, "convert_format")

def _op_write_csv(kwargs: dict) -> dict:
    file_path = kwargs.get("file_path")
    data = kwargs.get("data", [])
    if not file_path or not data:
        return _op_result("XLSX", "file_path and data required", False, "write_csv")
    out_path = _resolve_path(file_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(out_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(data)
        return _op_result("XLSX", f"Wrote CSV with {len(data)} rows", True, "write_csv", 
                        {"output_path": str(out_path), "rows": len(data)}, 
                        f"Wrote {len(data)} rows to {out_path.name}")
    except Exception as e:
        return _op_result("XLSX", f"CSV write failed: {e}", False, "write_csv")

_OPERATIONS = {
    "create_xlsx": _op_create_xlsx,
    "read_xlsx": _op_read_xlsx,
    "read_csv": _op_read_csv,
    "write_csv": _op_write_csv,
    "add_formula": _op_add_formula,
    "add_chart": _op_add_chart,
    "clean_data": _op_clean_data,
    "recalculate": _op_recalculate,
    "convert_format": _op_convert_format,
    "write_csv": _op_write_csv,
}

def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "XLSX",
            "summary": f"Unknown operation '{operation}'. Available: {', '.join(sorted(_OPERATIONS))}",
            "spoken_narrative": f"Unknown XLSX operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        return handler(kwargs)
    except Exception as exc:
        return {
            "title": "XLSX",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"XLSX error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return _op_result("XLSX", f"Chart type: {chart_type}, Range: {data_range}. openpyxl has limited chart support. Use pandas + matplotlib or convert to CSV and use Python plotting.", False, "add_chart")