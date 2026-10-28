satnum = "25544"
inclo = " 51.6337"
nodeo = " 11.7282"
ecco = "0006920"
argpo = "310.9581"
mo = " 49.0806"
no = "15.49059766"
elnum = "   0"

line = "2 " + satnum + " " + inclo + " " + nodeo + " " + ecco + " " + argpo + " " + mo + " " + no + " " + elnum
total = sum(int(ch) for ch in line if ch.isdigit()) + line.count("-")
line += str(total % 10)
print(len(line), repr(line))

from core.astro.sgp4 import Satrec, _checksum_ok

print("checksum ok:", _checksum_ok(line))
sat = Satrec.twoline2rv("1 25544U 98067A   26299.20906838  .00006121  00000+0  11890-3 0  9995", line)
print("parsed:", sat.satnum, round(sat.no_kozai, 9), round(sat.checksum_verified, 3) if False else sat.checksum_verified)
