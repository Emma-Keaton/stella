import struct
import zipfile

with zipfile.ZipFile("dist/Stella-Connect-1.0.0-android.apk") as archive:
    raw = archive.read("AndroidManifest.xml")

# String pool
string_count = 138
strings_start = 580
data_start = 8 + strings_start
pool = []
for index in range(string_count):
    offset = struct.unpack_from("<I", raw, 8 + 28 + 4 * index)[0]
    position = data_start + offset
    chars = struct.unpack_from("<H", raw, position)[0]
    pool.append(raw[position + 2:position + 2 + chars * 2].decode("utf-16-le", errors="replace"))

package_index = pool.index("package")
version_name_index = pool.index("versionName")
print("pool has package at", package_index, "versionName at", version_name_index)

start = 9616
chunk_size = 176
print("chunk size:", chunk_size)
for candidate in list(range(16, 33, 2)) + [36, 20, 24, 28, 32, 40]:
    if start + candidate + 20 > len(raw):
        continue
    block = raw[start + candidate:start + candidate + 20]
    ns, name, rv, typed = struct.unpack_from("<iiII", block, 0)
    data_type = typed >> 24
    payload = struct.unpack_from("<i", block, 16)[0]
    if 0 <= name < string_count:
        text = pool[name]
    else:
        text = "?"
    plausible = name in (package_index, version_name_index, pool.index("versionCode")
                         if "versionCode" in pool else -1)
    print("  start=%3d ns=%3d name=%3d (%s) raw=%d typed=%#010x data=%d plausible=%s"
          % (candidate, ns, name, text[:16], rv, typed, payload, plausible))
