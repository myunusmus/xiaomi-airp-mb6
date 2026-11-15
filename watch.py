"""Poll every readable property every few seconds and log only what changes.

Usage: python watch.py --token <hex> [--ip <ip>] [--seconds 600] [--interval 3] [--out watch.log]
"""
import argparse, json, sys, time
import miio

PROPS = [(2, 1), (2, 2), (2, 3), (2, 4), (2, 6), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (3, 9),
         (4, 1), (4, 2), (4, 3), (6, 1), (6, 2), (7, 1), (8, 1), (9, 1),
         (11, 1), (11, 2), (11, 3), (11, 4), (11, 5), (12, 1),
         (13, 1), (13, 2), (13, 3), (13, 4), (13, 5), (13, 6), (13, 7), (13, 8), (13, 9), (13, 10), (13, 11),
         (14, 2), (14, 3)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    miio.add_args(ap)
    ap.add_argument("--seconds", type=int, default=600, help="how long to run")
    ap.add_argument("--interval", type=float, default=3)
    ap.add_argument("--out", help="log file (default: stdout)")
    a = ap.parse_args()
    out = open(a.out, "a", buffering=1) if a.out else sys.stdout

    def log(s):
        out.write(time.strftime("%H:%M:%S ") + s + "\n")
        out.flush()

    d, prev, t0 = None, {}, time.time()
    log("START")
    while time.time() - t0 < a.seconds:
        try:
            if d is None:
                d = miio.connect(a)
            cur = d.get(PROPS)
            if not prev:
                log("FIRST " + json.dumps({f"{k[0]}.{k[1]}": v for k, v in cur.items()}, ensure_ascii=False))
            for k, v in cur.items():
                if k in prev and prev[k] != v:
                    log(f"{k[0]}.{k[1]}: {prev[k]!r} -> {v!r}")
            prev = cur
        except Exception as e:
            log(f"ERROR {e}")
            d = None
        time.sleep(a.interval)
    log("END")


if __name__ == "__main__":
    main()
