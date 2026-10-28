import pathlib
import re

src = pathlib.Path("tests/test_signal_decoders.py").read_text(encoding="utf-8")
l1 = re.search(r'ISS_TLE_1 = "([^"]+)"', src).group(1)
l2 = re.search(r'ISS_TLE_2 = "([^"]+)"', src).group(1)
for name, line in (("l1", l1), ("l2", l2)):
    print(name, len(line), repr(line))
    total = 0
    for ch in line[:68]:
        if ch.isdigit():
            total += int(ch)
        elif ch == "-":
            total += 1
    print("   computed:", total % 10, "stored:", line[68])
