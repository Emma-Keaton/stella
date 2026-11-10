import struct
import zlib
import os

def create_png(width, height, r, g, b, a=255):
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'  # filter byte
        for x in range(width):
            raw_data += struct.pack('BBBB', r, g, b, a)
    
    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr_crc = struct.pack('>I', zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff)
    ihdr = b'IHDR' + ihdr_data + ihdr_crc
    
    # IDAT chunk
    raw_data_compressed = zlib.compress(raw_data)
    idat = b'IDAT' + raw_data_compressed + struct.pack('>I', zlib.crc32(raw_data_compressed) & 0xffffffff)
    
    # IEND chunk
    iend = b'IEND' + struct.pack('>I', zlib.crc32(b'IEND') & 0xffffffff)
    
    png = b'\x89PNG\r\n\x1a\n' + ihdr + idat + iend
    return png

sizes = [48, 72, 96, 144, 192]
density_names = ['mipmap-mdpi', 'mipmap-hdpi', 'mipmap-xhdpi', 'mipmap-xxhdpi', 'mipmap-xxxhdpi']

base_dir = 'E:/Projects/stella/android/app/src/main/res'

for size, density in zip(sizes, density_names):
    img = create_png(size, size, 0, 229, 163, 255)  # Stella teal color
    
    dir_path = os.path.join(base_dir, density)
    os.makedirs(dir_path, exist_ok=True)
    
    # Write ic_launcher.png
    with open(os.path.join(dir_path, 'ic_launcher.png'), 'wb') as f:
        f.write(img)
    
    # Write ic_launcher_round.png
    with open(os.path.join(dir_path, 'ic_launcher_round.png'), 'wb') as f:
        f.write(img)
    
    print(f'Created {density}/ic_launcher.png and ic_launcher_round.png ({size}x{size})')

print('All mipmap icons created!')