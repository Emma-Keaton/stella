import struct
import zipfile

with zipfile.ZipFile("dist/Stella-Connect-1.0.0-android.apk") as archive:
    raw = archive.read("AndroidManifest.xml")

start = 9616  # first start-tag chunk
chunk_type, chunk_hdr, chunk_size = struct.unpack_from("<HHI", raw, start)
print("chunk: type=%#06x hdr=%d size=%d" % (chunk_type, chunk_hdr, chunk_size))
labels = {
    "line": struct.unpack_from("<I", raw, start + 8)[0],
    "comment": struct.unpack_from("<I", raw, start + 12)[0],
    "field16_i": struct.unpack_from("<i", raw, start + 16)[0],
    "field20_i": struct.unpack_from("<i", raw, start + 20)[0],
    "field20_H": struct.unpack_from("<H", raw, start + 20)[0],
    "field22_H": struct.unpack_from("<H", raw, start + 22)[0],
    "field24_H": struct.unpack_from("<H", raw, start + 24)[0],
    "field26_H": struct.unpack_from("<H", raw, start + 26)[0],
    "field28_H": struct.unpack_from("<H", raw, start + 28)[0],
    "field30_H": struct.unpack_from("<H", raw, start + 30)[0],
    "field32_H": struct.unpack_from("<H", raw, start + 32)[0],
    "field34_H": struct.unpack_from("<H", raw, start + 34)[0],
}
for key, value in labels.items():
    print("  +%-2s %-12s %s" % (key.split("_")[-1], key, value))

print("first 40 bytes of the attribute area:")
attribute_start = labels["field20_H"] or 36
print("assuming attributes start at", start + attribute_start)
area = raw[start + attribute_start:start + attribute_start + 60]
for index in range(3):
    block = area[index * 20:(index + 1) * 20]
    print("  attr", index, "ns=%d name=%d raw=%d typed=%#010x"
          % (struct.unpack_from("<i", block, 0)[0], struct.unpack_from("<i", block, 4)[0],
             struct.unpack_from("<i", block, 8)[0], struct.unpack_from("<I", block, 12)[0]))
