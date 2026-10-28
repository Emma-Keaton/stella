import os
data = open('features/anatomy/build.mjs', 'rb').read()
modified = data.replace(b'import * as k from "./kit/iso-kit.mjs";\n', b'')
temp_path = os.path.join(os.environ['TEMP'], 'build_no_kit.mjs')
open(temp_path, 'wb').write(modified)
print('written to', temp_path)
