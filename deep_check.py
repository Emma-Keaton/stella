import os, re

www_dir = 'E:/Projects/stella/android/app/src/main/assets/www'

# Read the raw HTML
with open(os.path.join(www_dir, 'index.html'), 'rb') as f:
    raw = f.read()

content = raw.decode('utf-8', errors='ignore')

# Find ALL remaining references that start with / followed by a path
# These would break on file:// URLs
patterns = [
    (r'href="(/[^"]+)', 'href'),
    (r"href='(/[^']+)'", 'href-single'),
    (r'src="(/[^"]+)', 'src'),
    (r"src='(/[^']+)'", 'src-single'),
    (r'url\((/[^)]+)\)', 'css-url'),
    (r'":(/[^"\']+)', 'json-colon-dq'),
    (r"':(/[^'\"]+)", 'json-colon-sq'),
]

total = 0
for pattern, label in patterns:
    matches = re.findall(pattern, content)
    if matches:
        print(f'{label}: {len(matches)} refs')
        for m in matches[:10]:
            print(f'  {m[:120]}')
        total += len(matches)

print(f'\nTotal absolute path references: {total}')

# Check specifically for __next_f data patterns
next_f_refs = re.findall(r'HL\[([^\]]+)\]', content)
print(f'\n__next_f HL patterns: {len(next_f_refs)}')
for ref in next_f_refs[:10]:
    print(f'  {ref[:120]}')