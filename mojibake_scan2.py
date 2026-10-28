import os

patterns = ['\u00e2\u20ac\u201d', '\u00e2\u2014', '\u00f0\u009f', '\u00e2\u20ac\u2122', '\u00c3\u00a9', '\u00e2\u20ac\u201c']
pattern_names = ['â€"', 'â—', 'ðŸ', 'â€™', 'Ã©', 'â€œ']

for root, dirs, files in os.walk(r'E:\Projects\stella'):
    dirs[:] = [d for d in dirs if d not in ('.venv', 'build', 'dist', '__pycache__', '.pytest_cache', '.github')]
    for f in files:
        if f.endswith('.py') and f != 'mojibake_scan.py' and f != 'mojibake_scan2.py':
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8') as fp:
                    content = fp.read()
                for pat, name in zip(patterns, pattern_names):
                    if pat in content:
                        print(f'{path}: found {name!r}')
            except Exception as e:
                pass