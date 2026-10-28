with open(r'E:\Projects\stella\main.py', 'r', encoding='utf-8') as f:
    c = f.read()
patterns = ['\u00e2\u20ac\u201d', '\u00e2\u2014', '\u00f0\u009f', '\u00e2\u20ac\u2122', '\u00c3\u00a9', '\u00e2\u20ac\u201c']
pattern_names = ['â€"', 'â—', 'ðŸ', 'â€™', 'Ã©', 'â€œ']
for pat, name in zip(patterns, pattern_names):
    if pat in c:
        print(f'main.py: found {name!r}')