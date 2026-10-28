import os
files = [
    r'E:\Projects\stella\ui.py',
    r'E:\Projects\stella\todo.md',
]
for path in files:
    if not os.path.exists(path): continue
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        text = raw.decode('utf-8')
        # check mojibake
        if 'â' in text:
            fixed = raw.decode('latin-1')
            # attempt re-encode
            with open(path, 'wb') as f:
                f.write(fixed.encode('utf-8'))
            print('Fixed', path)
        else:
            print('No mojibake', path)
    except Exception as e:
        print('Error', path, e)
