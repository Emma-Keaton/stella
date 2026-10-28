import os
import re
from collections import defaultdict

root = r"E:\Projects\stella"
patterns = [
    'â€',
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

regex = re.compile('|'.join(re.escape(p) for p in patterns))

exclude_dirs = {
    'dist','build','__pycache__','.git','.venv','node_modules','.pytest_cache','_internal','intermediates','app/build'
}
exclude_files = {
    'scan_mojibake.py','scan_mojibake_clean.py','mojibake_scan.py','mojibake_scan2.py','check_main_mojibake.py','mojibake_report.txt'
}

text_exts = {'.py','.md','.txt','.ps1','.sh','.json','.html','.js','.ts','.yml','.yaml','.ini','.conf','.spec','.iss','.xml','.rst','.toml','.cfg','.bat','.vbs','.markdown'}

counts = {}

for dirpath, dirnames, filenames in os.walk(root):
    # prune excluded dirs
    dirnames[:] = [d for d in dirnames if d not in exclude_dirs and not d.startswith('.')]
    rel_dir = os.path.relpath(dirpath, root)
    if any(ex in rel_dir.split(os.sep) for ex in exclude_dirs):
        continue
    for fname in filenames:
        if fname in exclude_files:
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext not in text_exts:
            continue
        fpath = os.path.join(dirpath, fname)
        # skip if path contains excluded dirs
        if any(ex in fpath for ex in [os.sep+'dist'+os.sep, os.sep+'build'+os.sep]):
            continue
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            continue
        matches = regex.findall(content)
        if matches:
            counts[fpath] = len(matches)

sorted_files = sorted(counts.items(), key=lambda x: x[1], reverse=True)
print(f"Found {len(sorted_files)} source files with mojibake")
for fp,cnt in sorted_files:
    print(f"{cnt}\t{fp}")

# write report
out = os.path.join(root, 'mojibake_source_report.txt')
with open(out,'w',encoding='utf-8') as f:
    f.write(f"Files: {len(sorted_files)}\n\n")
    for fp,cnt in sorted_files:
        f.write(f"{cnt}\t{fp}\n")
print('Report:', out)
