import re
with open('E:/Projects/stella/ui_dump.xml', 'r', encoding='utf-8') as f:
    content = f.read()
# Find all nodes with text and bounds
pattern = r'<node[^>]*text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
matches = re.findall(pattern, content)
for text, x1, y1, x2, y2 in matches:
    if text.strip():
        cx = (int(x1) + int(x2)) // 2
        cy = (int(y1) + int(y2)) // 2
        try:
            print(f"TEXT: {repr(text)}  CENTER: ({cx},{cy})")
        except UnicodeEncodeError:
            print(f"TEXT: {repr(text.encode('ascii', errors='replace').decode('ascii'))}  CENTER: ({cx},{cy})")