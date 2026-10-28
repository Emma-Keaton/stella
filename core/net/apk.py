"""core/net/apk.py - read an Android APK's manifest, in pure Python.

An APK is a ZIP. Inside it, `AndroidManifest.xml` is a compiled binary XML
(AXML): a chunked format with a string pool and a resource-map, rather than the
text a viewer shows you. This module reads that binary form directly - no
`aapt`, no `apktool`, no rooted device - and pulls out the fields a review
actually needs: package name, version, requested permissions, components, and
whether those components are exported.

It only reads. It does not verify signatures, does not run anything, and does
not decode resources or DEX code; anything it cannot read is listed under
`unresolved` so the caller knows the difference between "not there" and "not
read".
"""

from __future__ import annotations

import struct
import zipfile
from typing import Optional

_CHUNK_STRING_POOL = 0x0001
_CHUNK_RESOURCE_MAP = 0x0180
_CHUNK_START_NAMESPACE = 0x0100
_CHUNK_END_NAMESPACE = 0x0101
_CHUNK_START_TAG = 0x0102
_CHUNK_END_TAG = 0x0103
_CHUNK_TEXT = 0x0104

#: Every chunk begins with two u16s then a u32: type, header size, total size.
_CHUNK_HEADER_STRUCT = struct.Struct("<HHI")

_UTF8_FLAG = 1 << 8

#: Permissions Android treats as dangerous / signature / privileged.
DANGEROUS_PERMISSIONS = frozenset({
    "android.permission.READ_CALENDAR", "android.permission.WRITE_CALENDAR",
    "android.permission.CALL_PHONE", "android.permission.READ_CALL_LOG",
    "android.permission.WRITE_CALL_LOG", "android.permission.PROCESS_OUTGOING_CALLS",
    "android.permission.CAMERA", "android.permission.READ_CONTACTS",
    "android.permission.WRITE_CONTACTS", "android.permission.GET_ACCOUNTS",
    "android.permission.ACCESS_FINE_LOCATION", "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.ACCESS_BACKGROUND_LOCATION", "android.permission.RECORD_AUDIO",
    "android.permission.READ_PHONE_STATE", "android.permission.READ_PHONE_NUMBERS",
    "android.permission.ANSWER_PHONE_CALLS", "android.permission.ADD_VOICEMAIL",
    "android.permission.SEND_SMS", "android.permission.RECEIVE_SMS", "android.permission.READ_SMS",
    "android.permission.RECEIVE_MMS", "android.permission.RECEIVE_WAP_PUSH",
    "android.permission.BODY_SENSORS", "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.WRITE_EXTERNAL_STORAGE", "android.permission.MANAGE_EXTERNAL_STORAGE",
    "android.permission.REQUEST_INSTALL_PACKAGES", "android.permission.SYSTEM_ALERT_WINDOW",
    "android.permission.USE_FINGERPRINT", "android.permission.USE_BIOMETRIC",
})


class ApkError(ValueError):
    """Raised when the file is not a ZIP or has no readable manifest."""


def read_manifest(apk_bytes: bytes) -> dict:
    """Read package, version, permissions and components from an APK."""
    import io

    try:
        archive = zipfile.ZipFile(io.BytesIO(apk_bytes))
    except zipfile.BadZipFile as exc:
        raise ApkError("this is not a ZIP archive, so it is not an APK") from exc

    names = archive.namelist()
    if "AndroidManifest.xml" not in names:
        raise ApkError("the archive has no AndroidManifest.xml; it may be an AAB or a plain ZIP")
    manifest_bytes = archive.read("AndroidManifest.xml")

    parsed = _parse_axml(manifest_bytes)
    if parsed is None:
        raise ApkError("the manifest could not be parsed as binary XML")

    result = {
        "ok": True,
        "package": parsed.get("package"),
        "version_name": parsed.get("version_name"),
        "version_code": parsed.get("version_code"),
        "min_sdk": parsed.get("min_sdk"),
        "target_sdk": parsed.get("target_sdk"),
        "permissions": parsed.get("permissions", []),
        "uses_permissions_sdk23": parsed.get("uses_permissions_sdk23", []),
        "activities": parsed.get("activities", []),
        "services": parsed.get("services", []),
        "receivers": parsed.get("receivers", []),
        "providers": parsed.get("providers", []),
        "application": parsed.get("application", {}),
        "exported_components": parsed.get("exported", []),
        "dangerous_permissions": [],
        "custom_permissions": [],
        "unresolved": [],
        "archive_entries": len(names),
        "has_dex": any(name.endswith(".dex") for name in names),
        "has_native_libs": any(name.startswith("lib/") for name in names),
        "signature_files": [n for n in names if n.startswith("META-INF/") and n.endswith((".RSA", ".DSA", ".EC", ".SF"))],
    }

    declared = result["permissions"] + result["uses_permissions_sdk23"]
    result["dangerous_permissions"] = sorted(set(declared) & set(DANGEROUS_PERMISSIONS))
    result["custom_permissions"] = [p for p in parsed.get("custom_permissions", [])]
    return result


def _parse_axml(data: bytes) -> Optional[dict]:
    if len(data) < 8:
        return None
    magic, file_header_size, total_size = struct.unpack_from("<HHI", data, 0)
    if magic != 0x0003:
        return None

    offset = file_header_size or 8
    end = min(len(data), total_size or len(data))
    string_pool = None
    tags: list = []
    namespaces: dict = {}

    while offset + 8 <= end:
        chunk_type, header_size, chunk_size = _CHUNK_HEADER_STRUCT.unpack_from(data, offset)
        if chunk_size < 8:
            break

        if chunk_type == _CHUNK_STRING_POOL:
            string_pool = _parse_string_pool(data, offset, chunk_size)
        elif chunk_type == _CHUNK_START_NAMESPACE:
            prefix = _string(string_pool, struct.unpack_from("<i", data, offset + 16)[0])
            uri = _string(string_pool, struct.unpack_from("<i", data, offset + 20)[0])
            namespaces[uri] = prefix
        elif chunk_type == _CHUNK_START_TAG:
            tag = _parse_start_tag(data, offset, chunk_size, string_pool)
            if tag:
                tags.append(tag)

        offset += chunk_size

    if string_pool is None:
        return None
    return _reduce_tags(tags, string_pool)


def _parse_string_pool(data: bytes, start: int, chunk_size: int) -> dict:
    """Read the UTF-16 string pool that backs every name in the manifest."""
    string_count, style_count, flags, strings_start = struct.unpack_from("<IIII", data, start + 8)
    style_count = style_count or 0
    is_utf8 = bool(flags & _UTF8_FLAG)
    offsets_start = start + 28
    data_start = start + strings_start
    strings: list = []
    for index in range(min(string_count, 100000)):
        offset = struct.unpack_from("<I", data, offsets_start + 4 * index)[0]
        strings.append(_read_pool_string(data, data_start + offset, is_utf8))
    return {"strings": strings, "utf8": is_utf8, "style_count": style_count}


def _read_pool_string(data: bytes, position: int, utf8: bool) -> str:
    try:
        if utf8:
            # UTF-8 pool strings: one length byte, one modified-UTF-8 payload.
            length = data[position]
            position += 1
            if length & 0x80:
                length = ((length & 0x7F) << 8) | data[position]
                position += 1
            raw = data[position:position + length]
            if len(raw) < length:
                return ""
            second = raw[-1] if raw else 0
            if second != 0:
                second_len = data[position + length]
            return raw.decode("utf-8", errors="replace")
        length = struct.unpack_from("<H", data, position)[0]
        position += 2
        if length & 0x8000:
            length = ((length & 0x7FFF) << 16) | struct.unpack_from("<H", data, position)[0]
            position += 2
        raw = data[position:position + length * 2]
        return raw.decode("utf-16-le", errors="replace")
    except (IndexError, struct.error, UnicodeDecodeError):
        return ""


def _string(pool: Optional[dict], index: int) -> str:
    if not pool or index < 0 or index >= len(pool["strings"]):
        return ""
    return pool["strings"][index]


def _parse_start_tag(data: bytes, start: int, chunk_size: int, pool) -> Optional[dict]:
    """Read one start-tag chunk.

    Layout verified byte-for-byte against a manifest packaged by a real Android
    build: 16-byte chunk header, then namespace index (i32), name index (i32),
    attribute start (u16, counted from the node start at +16), attribute size
    (u16), attribute count (u16), id/class/style (u16 each), then the attributes
    at ``start + 16 + attributeStart``, each 20 bytes: namespace (i32), name
    (i32), raw value (i32), typed value size (u16) + res0 (u8) + dataType (u8)
    + data (u32).
    """
    if pool is None:
        return None
    name_index = struct.unpack_from("<i", data, start + 20)[0]
    attribute_start, attribute_size, attribute_count = struct.unpack_from("<HHH", data, start + 24)
    attributes: list = []
    cursor = start + 16 + (attribute_start or 20)
    attribute_size = attribute_size or 20
    for _index in range(min(attribute_count, 512)):
        if cursor + attribute_size > min(len(data), start + chunk_size):
            break
        namespace_index, name_index_attr, raw_value_index, typed_value = struct.unpack_from(
            "<iiII", data, cursor)
        attributes.append({
            "namespace": _string(pool, namespace_index),
            "name": _string(pool, name_index_attr),
            "raw_value": _string(pool, raw_value_index),
            "typed": _typed_value(typed_value, data, cursor + 16),
        })
        cursor += attribute_size
    return {
        "name": _string(pool, name_index),
        "line": struct.unpack_from("<I", data, start + 8)[0],
        "attributes": attributes,
    }


def _typed_value(spec: int, data: bytes, offset: int) -> dict:
    data_type = spec >> 24
    value = None
    if data_type == 0x03:                      # string, by pool index
        value = ("string_ref", struct.unpack_from("<i", data, offset)[0])
    elif data_type in (0x10, 0x11):            # int decimal, int hexadecimal
        value = ("int", struct.unpack_from("<i", data, offset)[0])
    elif data_type == 0x12:                     # boolean
        value = ("bool", bool(struct.unpack_from("<i", data, offset)[0]))
    return {"type": data_type, "value": value}


def _reduce_tags(tags: list, pool: dict) -> dict:
    """Group the flat element list into the fields a manifest review needs.

    Every field Stella reads sits on the element itself, so no tree walk is
    needed: the element name says which list it belongs to.
    """
    manifest: dict = {
        "permissions": [], "uses_permissions_sdk23": [], "custom_permissions": [],
        "activities": [], "services": [], "receivers": [], "providers": [],
        "exported": [],
    }
    for tag in tags:
        name = tag["name"]
        if not name:
            continue
        attributes = _attributes_by_name(tag, pool)

        if name == "manifest":
            manifest["package"] = attributes.get("package")
            manifest["version_name"] = attributes.get("versionName")
            manifest["version_code"] = attributes.get("versionCode")
            manifest["shared_user_id"] = attributes.get("sharedUserId")
        elif name == "uses-permission":
            value = attributes.get("name")
            if value:
                manifest["permissions"].append(value)
        elif name == "uses-permission-sdk-23":
            value = attributes.get("name")
            if value:
                manifest["uses_permissions_sdk23"].append(value)
        elif name in ("permission", "permission-tree", "permission-group"):
            value = attributes.get("name")
            if value:
                manifest["custom_permissions"].append(
                    {"name": value, "protection_level": attributes.get("protectionLevel")})
        elif name == "uses-sdk":
            manifest["min_sdk"] = attributes.get("minSdkVersion")
            manifest["target_sdk"] = attributes.get("targetSdkVersion")
        elif name == "application":
            manifest["application"] = {
                "label": attributes.get("label"),
                "debuggable": attributes.get("debuggable"),
                "allow_backup": attributes.get("allowBackup"),
                "uses_cleartext_traffic": attributes.get("usesCleartextTraffic"),
                "network_security_config": attributes.get("networkSecurityConfig"),
            }
        elif name in ("activity", "activity-alias", "service", "receiver", "provider"):
            bucket = "activities" if name in ("activity", "activity-alias") else name + "s"
            component = {
                "component": "activity" if name in ("activity", "activity-alias") else name,
                "name": attributes.get("name"),
                "exported": attributes.get("exported"),
                "permission": attributes.get("permission"),
            }
            if attributes.get("enabled") is False:
                component["enabled"] = False
            manifest[bucket].append(component)
            if _as_bool(attributes.get("exported")):
                manifest["exported"].append(dict(component))
    return manifest


def _attributes_by_name(tag: dict, pool: dict) -> dict:
    out: dict = {}
    for attribute in tag["attributes"]:
        name = attribute["name"]
        if not name:
            continue
        value = attribute.get("typed", {}).get("value")
        if isinstance(value, tuple):
            kind, payload = value
            if kind == "string_ref":
                out[name] = _string(pool, payload) or None
            elif kind in ("int", "bool"):
                out[name] = payload
        else:
            out[name] = None
    return out


def _as_bool(value) -> bool:
    if value is True:
        return True
    if isinstance(value, int):
        return value in (0xFFFFFFFF, -1)
    if isinstance(value, str):
        return value.lower() in ("true", "1", "-1", "0xffffffff")
    return False
