import re
with open('E:/Projects/stella/ui_dump.xml', 'r', encoding='utf-8') as f:
    content = f.read()
packages = re.findall(r'package="([^"]*)"', content)
print(set(packages))