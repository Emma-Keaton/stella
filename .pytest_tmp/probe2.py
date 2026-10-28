import re
import xml.etree.ElementTree as ET

content = (
    b"%PDF-1.7\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Count 3 >>\nendobj\n"
    b"trailer\n<< /Info 4 0 R >>\nstartxref\n0\n%%EOF\n"
    b"4 0 obj\n<< /Author (Alice Liddell) /Creator (Write) /Producer (AcmePDF 3.2) >>\nendobj\n"
)
print("regex /Type /Page[^s] hits:", len(re.findall(rb"/Type\s*/Page[^s]", content)))
print("/Count hits:", re.findall(rb"/Count\s+(\d+)", content))

xml = b"<?xml version='1.0'?><cp:coreProperties xmlns:cp='x' xmlns:dc='x'><dc:creator>Bob</dc:creator><cp:lastModifiedBy>Carol</cp:lastModifiedBy></cp:coreProperties>"
root = ET.fromstring(xml)
for element in root.iter():
    print(" tag:", element.tag, "text:", element.text, "attrs:", element.attrib)
