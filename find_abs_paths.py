import os, re

www_dir = 'E:/Projects/stella/android/app/src/main/assets/www'

abs_refs = []
for root, dirs, files in os.walk(www_dir):
    for fname in files:
        fpath = os.path.join(root, fname)
        # Skip binary files
        if fname.endswith(('.woff2', '.png', '.ico', '.jpg', '.webp', '.svg')):
            continue
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            continue
        
        rel_path = os.path.relpath(fpath, www_dir)
        
        # Find absolute path references (starting with /)
        patterns = [
            (r'href="\/[^"\']+', 'href'),
            (r'src="\/[^"\']+', 'src'),
            (r"url\(/[^)]+\)", 'css-url'),
        ]
        
        for pattern, attr_type in patterns:
            for m in re.finditer(pattern, content):
                line_num = content[:m.start()].count('\n') + 1
                abs_refs.append((rel_path, line_num, attr_type, m.group()[:100]))

print(f'Total absolute path references: {len(abs_refs)}')
for ref in abs_refs:
    print(f'  {ref[0]}:{ref[1]} [{ref[2]}] - {ref[3]}')