import os
import re
from collections import defaultdict

root = r"E:\Projects\stella"
patterns = [
    'â€',   # em dash start
    'â—',
    'â€¢',
    'Ã©',
    'Ã¢',
    'Ã®',
    'â‚¬',
    'â€“',
    'â€¦',
    'â€œ',
    'â€',
    'â€™',
    'â€˜',
]

# compile as regex alternation
regex = re.compile('|'.join(re.escape(p) for p in patterns))

counts = defaultdict(int)
files_found = set()

# extensions to scan
text_exts = {'.py','.md','.txt','.ps1','.sh','.json','.html','.js','.ts','.yml','.yaml','.ini','.conf','.spec','.iss','.xml','.rst','.md','.toml','.cfg','.bat','.vbs','.markdown'}

for dirpath, dirnames, filenames in os.walk(root):
    # skip hidden dirs
    dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in ('.git','__pycache__','node_modules','.venv')]
    for fname in filenames:
        ext = os.path.splitext(fname)[1].lower()
        if ext not in text_exts:
            # still try small files?
            continue
        fpath = os.path.join(dirpath, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            continue
        matches = regex.findall(content)
        if matches:
            counts[fpath] = len(matches)
            files_found.add(fpath)

# sort by count descending
sorted_files = sorted(counts.items(), key=lambda x: x[1], reverse=True)

print(f"Found {len(sorted_files)} files with mojibake patterns")
for fp, cnt in sorted_files:
    print(f"{cnt}\t{fp}")

# Also write to file
out_path = os.path.join(root, 'mojibake_report.txt')
with open(out_path, 'w', encoding='utf-8') as out:
    out.write(f"Found {len(sorted_files)} files\n\n")
    for fp, cnt in sorted_files:
        out.write(f"{cnt}\t{fp}\n")
print(f"Report written to {out_path}")
