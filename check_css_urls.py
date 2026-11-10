import re

css_path = 'E:/Projects/stella/android/app/src/main/assets/www/_next/static/css/f68621d36279a3ec.css'
with open(css_path, 'r', encoding='utf-8') as f:
    css = f.read()

abs_urls = re.findall(r'url\("([^"]+)"\)', css)
abs_urls += re.findall(r"url\('([^']+)'\)", css)
abs_urls += re.findall(r'url\(([^)]+)\)', css)

absolute_refs = [u.strip() for u in abs_urls if u.strip().startswith('/') or u.strip().startswith('http')]
print(f'Total URL references in CSS: {len(abs_urls)}')
print(f'Absolute URL references: {len(absolute_refs)}')
for u in absolute_refs[:20]:
    print(f'  {u}')