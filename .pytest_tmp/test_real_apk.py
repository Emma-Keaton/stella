import sys
import zipfile

from core.net.apk import read_manifest

for path in ("dist/Stella-Connect-1.0.0-android.apk",):
    print("===", path)
    with open(path, "rb") as handle:
        data = handle.read()
    try:
        result = read_manifest(data)
    except Exception as exc:
        print("ERROR:", type(exc).__name__, exc)
        continue
    print("package:", result["package"])
    print("version:", result["version_name"], result["version_code"])
    print("min/target sdk:", result["min_sdk"], result["target_sdk"])
    print("permissions:", len(result["permissions"]), result["permissions"][:5])
    print("dangerous:", len(result["dangerous_permissions"]), result["dangerous_permissions"][:5])
    print("activities:", len(result["activities"]), result["activities"][:2])
    print("exported:", len(result["exported_components"]), result["exported_components"][:3])
    print("application:", result["application"])
    print("has_dex:", result["has_dex"], "| has_native:", result["has_native_libs"])
    print("signatures:", result["signature_files"][:3])
    print("unresolved:", result["unresolved"])

    with zipfile.ZipFile(path) as archive:
        raw = archive.read("AndroidManifest.xml")
    print("manifest bytes:", len(raw), "first:", raw[:6].hex())
