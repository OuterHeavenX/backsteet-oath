#!/usr/bin/env python3
"""Checks that two Godot import caches hold the same pixels: every .ctex present in both directories is decoded
(every stored mip level) and compared value for value. Used to show that a different lossless WebP effort
(rendering/textures/webp_compression/compression_method) changes only the file size.

Usage: python3 tools/perf/verify_ctex_pixels.py <imported dir A> <imported dir B>
Exit code 1 if any texture differs or cannot be compared.
"""
import io, os, struct, sys
import numpy as np
from PIL import Image


def levels(path):
    d = open(path, "rb").read()
    if d[:4] != b"GST2":
        return None
    off = 4 + 20 + 12
    data_format, w, h, mips, fmt = struct.unpack_from("<IHHII", d, off)
    off += 16
    out = []
    if data_format not in (1, 2):      # 1 = PNG, 2 = WebP (lossless or lossy); 0/3 = raw or Basis: compare bytes
        return [("raw", d[off:])]
    for _ in range(mips + 1):
        if off + 4 > len(d):
            break
        (sz,) = struct.unpack_from("<I", d, off)
        out.append(("img", d[off + 4: off + 4 + sz]))
        off += 4 + sz
    return out


def main():
    a_dir, b_dir = sys.argv[1], sys.argv[2]
    same = diff = missing = 0
    bytes_a = bytes_b = 0
    bad = []
    for name in sorted(os.listdir(a_dir)):
        if not name.endswith(".ctex"):
            continue
        pa, pb = os.path.join(a_dir, name), os.path.join(b_dir, name)
        if not os.path.exists(pb):
            missing += 1
            continue
        la, lb = levels(pa), levels(pb)
        ok = la is not None and lb is not None and len(la) == len(lb)
        if ok:
            for (ka, da), (kb, db) in zip(la, lb):
                if ka == "raw" or kb == "raw":
                    ok = ok and da == db
                else:
                    ia = np.asarray(Image.open(io.BytesIO(da)).convert("RGBA"))
                    ib = np.asarray(Image.open(io.BytesIO(db)).convert("RGBA"))
                    ok = ok and ia.shape == ib.shape and np.array_equal(ia, ib)
        if ok:
            same += 1
        else:
            diff += 1
            bad.append(name)
        bytes_a += os.path.getsize(pa)
        bytes_b += os.path.getsize(pb)
    print("textures compared: %d identical pixels, %d different, %d only in A" % (same, diff, missing))
    print("bytes: A %d  B %d  (%.1f%%)" % (bytes_a, bytes_b, 100.0 * bytes_b / max(bytes_a, 1)))
    for n in bad[:20]:
        print("  DIFFERENT:", n)
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
