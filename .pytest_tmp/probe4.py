import xml.etree.ElementTree as ET
import zipfile
import io

core_xml = (
    b"<?xml version='1.0'?><cp:coreProperties "
    b"xmlns:cp='x' xmlns:dc='x'><dc:creator>Bob</dc:creator>"
    b"<cp:lastModifiedBy>Carol</cp:lastModifiedBy>"
    b"<dcterms:created>2026-01-02T03:04:05Z</dcterms:created>"
    b"<cp:keywords>budget, secret</cp:keywords></cp:coreProperties>"
)
try:
    root = ET.fromstring(core_xml)
    print("parsed ok")
    for element in root.iter():
        print("  ", element.tag, repr(element.text))
except ET.ParseError as exc:
    print("PARSE ERROR:", exc)
    print(repr(core_xml[:80]))

buffer = io.BytesIO()
with zipfile.ZipFile(buffer, "w") as archive:
    archive.writestr("docProps/core.xml", core_xml)
with zipfile.ZipFile(buffer) as archive:
    print("read back len:", len(archive.read("docProps/core.xml")))
    print("first 40:", archive.read("docProps/core.xml")[:40])
