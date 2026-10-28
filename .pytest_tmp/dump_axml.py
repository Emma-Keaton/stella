import struct
import zipfile

path = "dist/Stella-Connect-1.0.0-android.apk"
with zipfile.ZipFile(path) as archive:
    raw = archive.read("AndroidManifest.xml")

print("size:", len(raw))
print("first 16:", raw[:16].hex(" "))

# Reference layout: u16 chunk type, u16 header size, u32 chunk size.
headers = {
    0x0003: "file-header",
    0x001C: "string-pool",
    0x0008: "resource-map",
    0x0100: "start-namespace",
    0x0101: "end-namespace",
    0x0102: "start-tag",
    0x0103: "end-tag",
    0x0104: "text",
    0x0140: "type-spec",
    0x0141: "type",
}

offset = 0
total = 0
if len(raw) >= 8:
    magic, header_size, total = struct.unpack_from("<HHI", raw, 0)
    print("file header: magic=%#06x header_size=%d total=%d" % (magic, header_size, total))
    offset = header_size

steps = 0
while offset + 8 <= min(len(raw), total) and steps < 60:
    chunk_type, header_size, chunk_size = struct.unpack_from("<HHI", raw, offset)
    name = headers.get(chunk_type, "unknown")
    extra = ""
    if chunk_type == 0x001C:
        string_count, style_count, flags, strings_start = struct.unpack_from("<IIII", raw, offset + 8)
        extra = "strings=%d styles=%d flags=%#x strings_start=%d" % (
            string_count, style_count, flags, strings_start)
    elif chunk_type == 0x0102:
        comment = struct.unpack_from("<I", raw, offset + 12)[0]
        name_index = struct.unpack_from("<i", raw, offset + 16)[0]
        attr_start, attr_size, attr_count = struct.unpack_from("<HHH", raw, offset + 20)
        extra = "name=%d attrStart=%d attrSize=%d attrCount=%d line=%d" % (
            name_index, attr_start, attr_size, attr_count,
            struct.unpack_from("<I", raw, offset + 8)[0])
    elif chunk_type in (0x0100, 0x0101):
        prefix = struct.unpack_from("<i", raw, offset + 16)[0]
        uri = struct.unpack_from("<i", raw, offset + 20)[0]
        extra = "prefix=%d uri=%d" % (prefix, uri)
    print("  off=%6d type=%#06x hdr=%3d size=%6d %-16s %s" % (
        offset, chunk_type, header_size, chunk_size, name, extra))
    if chunk_size <= 0:
        print("  non-positive size; stopping")
        break
    offset += chunk_size
    steps += 1
