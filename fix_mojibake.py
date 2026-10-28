import os
import sys

files_to_fix = [
    r'E:\Projects\stella\ui.py',
    r'E:\Projects\stella\assets\web_background\index_golden_orb_backup.html',
    r'E:\Projects\stella\stella-connect-android\app\src\main\assets\web_background\index_golden_orb_backup.html',
    r'E:\Projects\stella\dashboard\static\app.html',
    r'E:\Projects\stella\assets\web_background\index.html',
    r'E:\Projects\stella\stella-connect-android\app\src\main\assets\web_background\index.html',
    r'E:\Projects\stella\todo.md',
    r'E:\Projects\stella\installer\Stella.iss',
    r'E:\Projects\stella\dashboard\static\login.html',
    r'E:\Projects\stella\installer\Stella.spec',
    r'E:\Projects\stella\build.ps1',
    r'E:\Projects\stella\update.ps1',
]

for path in files_to_fix:
    if not os.path.exists(path):
        print(f'Skip missing {path}')
        continue
    try:
        with open(path, 'r', encoding='utf-8', errors='strict') as f:
            data = f.read()
        # try to fix mojibake by re-decoding latin-1
        # If file contains typical mojibake, decode bytes via latin-1 then encode utf-8
        # Heuristic: if 'â' in data, attempt fix
        if 'â' in data or 'Ã' in data:
            # read raw bytes
            with open(path, 'rb') as f:
                raw = f.read()
            try:
                fixed = raw.decode('latin-1').encode('utf-8').decode('utf-8')
                # quick sanity: ensure no obvious mojibake left
                if 'â' not in fixed or fixed.count('â') < data.count('â'):
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(fixed)
                    print(f'Fixed {path}')
                    continue
            except Exception as e:
                print(f'Failed decode {path}: {e}')
                continue
        print(f'No fix needed {path}')
    except Exception as e:
        print(f'Error {path}: {e}')
