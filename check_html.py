import re

with open('E:/Projects/stella/android/app/src/main/assets/www/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Find all remaining absolute /_next references
refs = re.findall(r'"/_next[^"\']*', content)
refs2 = re.findall(r":/_next[^'\"]*", content)
refs3 = re.findall(r"'/_next[^'\"]*", content)

all_refs = refs + refs2 + refs3
print(f'Remaining absolute /_next references: {len(all_refs)}')
for r in all_refs[:20]:
    print(f'  {r[:100]}')

# Also check for other absolute refs
abs_refs = re.findall(r'href="\/[^"\']+', content)
abs_refs += re.findall(r'src="\/[^"\']+', content)
abs_refs += re.findall(r"url\(/[^)]+\)", content)
print(f'Other absolute references: {len(abs_refs)}')
for r in abs_refs[:10]:
    print(f'  {r[:100]}')