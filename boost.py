"""Cooking boost: switch to Favorite mode at a level chosen from PM2.5, return to Auto when the air is clean.

PM2.5 > 75 -> level 10, > 35 -> 8, otherwise 6. Returns to Auto after PM2.5 stays <= 8 for 3 minutes
(at least 5 minutes in total) or when --minutes runs out. Exits without touching anything if the mode
is changed by hand meanwhile.

Usage: python boost.py --token <hex> [--ip <ip>] [--minutes 30]
"""
import argparse, sys, time
import miio


def log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    miio.add_args(ap)
    ap.add_argument("--minutes", type=int, default=30, help="maximum run time")
    a = ap.parse_args()

    d = miio.connect(a)
    x = d.get([(2, 1), (2, 3), (9, 1), (3, 4), (13, 4)])
    pm = x[(3, 4)]
    lvl = 10 if pm > 75 else 8 if pm > 35 else 6
    log(f"before: mode={x[(2, 3)]} fav={x[(9, 1)]} pm2.5={pm} rpm={x[(13, 4)]} -> favorite level {lvl}")
    if not x[(2, 1)]:
        d.set(2, 1, True)
    d.set(9, 1, lvl)
    d.set(2, 3, 5)

    t0, clean = time.time(), 0
    while time.time() - t0 < a.minutes * 60:
        time.sleep(30)
        try:
            y = d.get([(3, 4), (13, 4), (2, 3)])
        except Exception as e:
            log(f"error {e}")
            try:
                d = miio.connect(a)
            except Exception:
                pass
            continue
        log(f"pm2.5={y[(3, 4)]} rpm={y[(13, 4)]} mode={y[(2, 3)]}")
        if y[(2, 3)] != 5:
            log("mode was changed by hand, leaving it alone")
            sys.exit()
        clean = clean + 1 if y[(3, 4)] <= 8 else 0
        if clean >= 6 and time.time() - t0 > 300:
            break
    d.set(2, 3, 0)
    log("back to auto")


if __name__ == "__main__":
    main()
