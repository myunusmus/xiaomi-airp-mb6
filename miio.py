"""Minimal miIO / MIoT client for the Xiaomi Mijia Smart Air Purifier MAX (xiaomi.airp.mb6).

Usage:
    python miio.py --token <hex> [--ip <ip>] <method> ['<json params>']
    python miio.py --tokens tokens.json <method> ['<json params>']

Examples:
    python miio.py --token 0123... miIO.info
    python miio.py --token 0123... get_properties '[{"did":"x","siid":3,"piid":4}]'

If --ip is omitted, the device is found by UDP broadcast on the local network.
"""
import argparse, hashlib, json, os, socket, sys, time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

MODEL = "xiaomi.airp.mb6"
PORT = 54321
HELLO = bytes.fromhex("21310020" + "ff" * 28)


def load(path, model=MODEL, did=None):
    """Find a device entry (dict with 'token') in a token-extractor JSON dump.

    Matches by did if given, otherwise by model. Returns the dict (has 'token', maybe 'localip', 'did')."""
    def match(x):
        if "token" not in x:
            return False
        if did is not None:
            return str(x.get("did")) == str(did)
        return x.get("model") == model

    def walk(x):
        if isinstance(x, dict):
            if match(x):
                return x
            for v in x.values():
                r = walk(v)
                if r:
                    return r
        elif isinstance(x, list):
            for v in x:
                r = walk(v)
                if r:
                    return r

    with open(path) as f:
        r = walk(json.load(f))
    if not r:
        raise LookupError(f"no device with {'did ' + str(did) if did else 'model ' + model} in {path}")
    return r


def discover(did=None, timeout=8, subnet=None):
    """Broadcast miIO hello and return {did: ip}. If did is given, return its ip as soon as it answers.

    subnet: optional prefix like '192.168.1' to also unicast to .1-.254 (helps when broadcast is filtered)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(0.5)
    targets = ["255.255.255.255"] + ([f"{subnet}.{i}" for i in range(1, 255)] if subnet else [])
    found = {}
    end = time.time() + timeout
    while time.time() < end:
        for h in targets:
            try:
                s.sendto(HELLO, (h, PORT))
            except OSError:
                pass
        try:
            while True:
                d, a = s.recvfrom(1024)
                if len(d) < 32:
                    continue
                dev = int.from_bytes(d[8:12], "big")
                found[dev] = a[0]
                if did is not None and dev == int(did):
                    return a[0]
        except socket.timeout:
            pass
    if did is not None:
        raise RuntimeError(f"device {did} not found on the network")
    return found


class Dev:
    def __init__(self, ip, token):
        self.ip, self.token = ip, bytes.fromhex(token)
        self.key = hashlib.md5(self.token).digest()
        self.iv = hashlib.md5(self.key + self.token).digest()
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.settimeout(4)
        self.id = int(time.time()) % 100000
        self.hello()

    def hello(self):
        for _ in range(3):
            try:
                self.s.sendto(HELLO, (self.ip, PORT))
                d, _a = self.s.recvfrom(4096)
                self.did_bytes = d[8:12]
                self.did = str(int.from_bytes(self.did_bytes, "big"))
                self.stamp = int.from_bytes(d[12:16], "big")
                self.t0 = time.time()
                return
            except socket.timeout:
                pass
        raise RuntimeError("hello timeout")

    def _c(self):
        return Cipher(algorithms.AES(self.key), modes.CBC(self.iv))

    def send(self, method, params, retries=3):
        for _ in range(retries):
            self.id += 1
            msg = json.dumps({"id": self.id, "method": method, "params": params}).encode()
            p = padding.PKCS7(128).padder()
            e = self._c().encryptor()
            enc = e.update(p.update(msg) + p.finalize()) + e.finalize()
            stamp = self.stamp + int(time.time() - self.t0) + 1
            head = b"\x21\x31" + (32 + len(enc)).to_bytes(2, "big") + b"\0" * 4 + self.did_bytes + stamp.to_bytes(4, "big")
            cs = hashlib.md5(head + self.token + enc).digest()
            self.s.sendto(head + cs + enc, (self.ip, PORT))
            try:
                while True:
                    d, _a = self.s.recvfrom(65535)
                    if len(d) <= 32:
                        continue
                    dcr = self._c().decryptor()
                    raw = dcr.update(d[32:]) + dcr.finalize()
                    u = padding.PKCS7(128).unpadder()
                    r = json.loads((u.update(raw) + u.finalize()).rstrip(b"\0"))
                    if r.get("id") == self.id:
                        return r
            except socket.timeout:
                self.hello()
        raise RuntimeError("no reply")

    def get(self, pairs):
        """Read MIoT properties. pairs: [(siid, piid), ...] -> {(siid, piid): value or 'ERR<code>'}"""
        out = {}
        for i in range(0, len(pairs), 10):
            chunk = pairs[i:i + 10]
            r = self.send("get_properties", [{"did": self.did, "siid": s, "piid": p} for s, p in chunk])
            for x in r.get("result", []):
                out[(x["siid"], x["piid"])] = x.get("value") if x.get("code") == 0 else f"ERR{x.get('code')}"
        return out

    def set(self, s, p, v):
        """Write one MIoT property."""
        return self.send("set_properties", [{"did": self.did, "siid": s, "piid": p, "value": v}])

    def action(self, s, a, args=()):
        """Call a MIoT action."""
        return self.send("action", {"did": self.did, "siid": s, "aiid": a, "in": list(args)})


def add_args(ap):
    """Common connection arguments for the scripts in this repo."""
    ap.add_argument("--token", default=os.environ.get("MIIO_TOKEN"), help="32-char hex token (or env MIIO_TOKEN)")
    ap.add_argument("--tokens", help="token-extractor JSON dump to read the token (and ip) from")
    ap.add_argument("--ip", default=os.environ.get("MIIO_IP"), help="device ip (or env MIIO_IP); omit to auto-discover")
    ap.add_argument("--did", default=os.environ.get("MIIO_DID"), help="device id, used for discovery / picking from --tokens")
    ap.add_argument("--subnet", help="e.g. 192.168.1 - also probe every host of this /24 during discovery")


def connect(args):
    """Build a Dev from parsed add_args() arguments."""
    token, ip, did = args.token, args.ip, args.did
    if args.tokens:
        e = load(args.tokens, did=did)
        token = token or e["token"]
        did = did or e.get("did")
        ip = ip or e.get("localip")
    if not token:
        sys.exit("need --token, MIIO_TOKEN or --tokens")
    if ip:
        try:
            return Dev(ip, token)
        except (RuntimeError, OSError):
            if not did:
                raise
    if did:
        return Dev(discover(did, subnet=args.subnet), token)
    found = discover(subnet=args.subnet)
    if len(found) != 1:
        sys.exit(f"found {len(found)} miIO devices {found}; pass --ip or --did")
    return Dev(next(iter(found.values())), token)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_args(ap)
    ap.add_argument("method")
    ap.add_argument("params", nargs="?", default="[]")
    a = ap.parse_args()
    dev = connect(a)
    r = dev.send(a.method, json.loads(a.params))
    if isinstance(r.get("result"), dict):  # don't print secrets from miIO.info
        r["result"].pop("token", None)
        r["result"].get("ap", {}).pop("ssid", None)
    print(json.dumps(r, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
