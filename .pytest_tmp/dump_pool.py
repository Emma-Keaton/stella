import struct
import zipfile

with zipfile.ZipFile("dist/Stella-Connect-1.0.0-android.apk") as archive:
    raw = archive.read("AndroidManifest.xml")

magic, header_size, total = struct.unpack_from("<HHI", raw, 0)
print("file header:", hex(magic), header_size, total)
offset = header_size
chunk_type, chunk_hdr, chunk_size = struct.unpack_from("<HHI", raw, offset)
print("first chunk: type=%#06x hdr=%d size=%d" % (chunk_type, chunk_hdr, chunk_size))
string_count, style_count, flags, strings_start = struct.unpack_from("<IIII", raw, offset + 8)
print("strings=%d styles=%d flags=%#x strings_start=%d" % (string_count, style_count, flags, strings_start))

offsets_start = offset + 28
data_start = offset + strings_start
print("data_start:", data_start, "offsets_start:", offsets_start)
first_offsets = [struct.unpack_from("<I", raw, offsets_start + 4 * i)[0] for i in range(5)]
print("first offsets:", first_offsets)

for index in range(6):
    position = data_start + first_offsets[index]
    chars = struct.unpack_from("<H", raw, position)[0]
    text = raw[position + 2:position + 2 + chars * 2].decode("utf-16-le", errors="replace")
    print(" ", index, "chars=", chars, repr(text))
