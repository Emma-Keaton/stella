"""Build a tiny AndroidManifest.xml (binary AXML) for the decoder test."""
import struct
import zipfile
import io

STRINGS = [
    "manifest", "package", "com.example.stellatest", "versionName", "versionCode",
    "uses-permission", "name", "android.permission.INTERNET",
    "android.permission.CAMERA", "application", "activity", "exported", "label",
    "com.example.stellatest.MainActivity", "http://schemas.android.com/apk/res/android",
    "android", "targetSdkVersion",
]


def _string_pool_chunk() -> bytes:
    utf16 = []
    encoded_strings = []
    for value in STRINGS:
        raw = value.encode("utf-16-le")
        utf16.append(raw)
        encoded_strings.append(raw)

    offsets = []
    data = b""
    for raw in encoded_strings:
        offsets.append(len(data))
        chars = len(raw) // 2
        if chars > 0x7FFF:
            raise ValueError("test string too long")
        data += struct.pack("<H", chars) + raw + struct.pack("<H", 0)

    strings_start = 28 + 4 * len(STRINGS)
    padded = data + b"\x00" * ((-len(data)) % 4)
    strings_start += 0
    header = struct.pack("<HH", 0x1C01, 0)
    chunk = struct.pack("<HHIIIIIII", 0x001C0001, 28 + 4 * len(STRINGS) + len(padded),
                        len(STRINGS), len(STRINGS), 0, 0, strings_start, 0) + \
        struct.pack("<" + "I" * len(offsets), *offsets) + padded
    return chunk


def _resource_map_chunk() -> bytes:
    return struct.pack("<HHII", 0x00080380, 8, 0, 0)


def _start_namespace(prefix_index: int, uri_index: int) -> bytes:
    body = struct.pack("<iII", prefix_index, uri_index, 0xFFFFFFFF)
    return struct.pack("<HHII", 0x00100100, 6 + len(body), 1, 0) + body


def _start_tag(name_index: int, attributes: list) -> bytes:
    attribute_bytes = b""
    for namespace_index, attribute_name_index, data_type, data in attributes:
        attribute_bytes += struct.pack("<iiII", namespace_index, attribute_name_index, 0, data)
    body = struct.pack("<iHHI", name_index, 0, len(attributes), 0xFFFFFFFF)
    chunk_size = 9 + len(body) + len(attribute_bytes)
    return (struct.pack("<HHII", 0x00100102, chunk_size, 1, 0xFFFFFFFF)
            + body + attribute_bytes)


def _end_tag(name_index: int) -> bytes:
    body = struct.pack("<iI", name_index, 0xFFFFFFFF)
    return struct.pack("<HHII", 0x00100103, 6 + len(body), 0, 0) + body


def build_manifest() -> bytes:
    android_index = STRINGS.index("android")
    manifest_index = STRINGS.index("manifest")
    uses_permission = STRINGS.index("uses-permission")
    application_index = STRINGS.index("application")
    activity_index = STRINGS.index("activity")

    parts = [
        struct.pack("<HHIIIIII", 0x0003, 0, 0, 0, 0, 0, 0, 0),
        _string_pool_chunk(),
        _resource_map_chunk(),
        _start_namespace(android_index, STRINGS.index("http://schemas.android.com/apk/res/android")),
    ]

    parts.append(_start_tag(manifest_index, [
        (-1, STRINGS.index("package"), 0x03, STRINGS.index("com.example.stellatest")),
        (-1, STRINGS.index("versionName"), 0x03, STRINGS.index("1.0")),
        (-1, STRINGS.index("versionCode"), 0x10, 7),
    ]))
    for permission in ("android.permission.INTERNET", "android.permission.CAMERA"):
        parts.append(_start_tag(uses_permission, [
            (-1, STRINGS.index("name"), 0x03, STRINGS.index(permission))]))
        parts.append(_end_tag(uses_permission))
    parts.append(_end_tag(manifest_index))

    parts.append(_start_tag(application_index, [
        (-1, android_index, 0x03, STRINGS.index("Stella Test")),
        (android_index, STRINGS.index("exported"), 0x12, 1),
        (android_index, STRINGS.index("targetSdkVersion"), 0x10, 34),
    ]))
    parts.append(_start_tag(activity_index, [
        (android_index, STRINGS.index("name"), 0x03, STRINGS.index("com.example.stellatest.MainActivity")),
        (android_index, STRINGS.index("exported"), 0x12, 1),
    ]))
    parts.append(_end_tag(activity_index))
    parts.append(_end_tag(application_index))
    parts.append(_end_tag(manifest_index))

    raw = b"".join(parts)
    total = 8 + len(raw)
    header = struct.pack("<HHIIIIII", 0x0003, 8, total, 0, 0, 0, 0, 0)
    return header + raw


def build_apk() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("AndroidManifest.xml", build_manifest())
        archive.writestr("classes.dex", b"dex\n035\x00")
        archive.writestr("res/layout/main.xml", b"<x/>")
    return buffer.getvalue()


if __name__ == "__main__":
    from core.net.apk import read_manifest

    result = read_manifest(build_apk())
    print(result)
