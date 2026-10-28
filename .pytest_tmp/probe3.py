import io
import zipfile

from core.docs.metadata import read

buffer = io.BytesIO()
with zipfile.ZipFile(buffer, "w") as archive:
    archive.writestr(
        "docProps/core.xml",
        b"<?xml version='1.0'?><cp:coreProperties "
        b"xmlns:cp='x' xmlns:dc='x'><dc:creator>Bob</dc:creator>"
        b"<cp:lastModifiedBy>Carol</cp:lastModifiedBy>"
        b"<dcterms:created>2026-01-02T03:04:05Z</dcterms:created>"
        b"<cp:keywords>budget, secret</cp:keywords></cp:coreProperties>")
    archive.writestr(
        "docProps/app.xml",
        b"<?xml version='1.0'?><Properties>"
        b"<Application>Microsoft Office Word</Application></Properties>")
    archive.writestr("word/document.xml", b"<w/>")

result = read(buffer.getvalue(), "notes.docx")
print("ok:", result["ok"], "format:", result["format"])
print("creator:", result["creator"])
print("raw core:", result.get("raw", {}).get("core"))
print("app:", result.get("raw", {}).get("app"))
