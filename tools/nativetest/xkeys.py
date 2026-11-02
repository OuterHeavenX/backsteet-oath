#!/usr/bin/env python3
"""Sends real X11 key events (XTest) to whatever has focus. Used to drive the exported native build under Xvfb.
Usage: xkeys.py "Return:0.1 wait:2 j:0.08 Right:0.5 ..."   (key:hold_seconds, or wait:seconds)"""
import ctypes, sys, time
x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
xtst = ctypes.cdll.LoadLibrary("libXtst.so.6")
x11.XOpenDisplay.restype = ctypes.c_void_p
x11.XStringToKeysym.restype = ctypes.c_ulong
x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
x11.XFlush.argtypes = [ctypes.c_void_p]
d = x11.XOpenDisplay(None)
if not d:
    sys.exit("no display")
for tok in " ".join(sys.argv[1:]).split():
    k, _, v = tok.partition(":")
    t = float(v or 0.08)
    if k == "wait":
        time.sleep(t)
        continue
    code = x11.XKeysymToKeycode(d, x11.XStringToKeysym(k.encode()))
    xtst.XTestFakeKeyEvent(d, code, 1, 0); x11.XFlush(d)
    time.sleep(t)
    xtst.XTestFakeKeyEvent(d, code, 0, 0); x11.XFlush(d)
    time.sleep(0.05)
