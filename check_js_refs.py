import os, re

www_dir = 'E:/Projects/stella/android/app/src/main/assets/www'
js_dir = os.path.join(www_dir, '_next/static/chunks')

abs_refs = []
for root, dirs, files in os.walk(js_dir):
    for fname in files:
        if not fname.endswith('.js'):
            continue
        fpath = os.path.join(root, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            continue
        
        rel_path = os.path.relpath(fpath, www_dir)
        
        # Look for absolute URL references
        patterns = [
            r'https?://[^"\'\\\s]+',
            r'ws://[^"\'\\\s]+',
            r'new WebSocket\(["\'][^\/]',
        ]
        
        for pattern in patterns:
            for m in re.finditer(pattern, content):
                line_num = content[:m.start()].count('\n') + 1
                abs_refs.append((rel_path, line_num, m.group()[:120]))

print(f'Total potential issues in JS: {len(abs_refs)}')
for ref in abs_refs[:30]:
    print(f'  {ref[0]}:{ref[1]} - {ref[2]}')