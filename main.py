#!/usr/bin/env python3
"""Meme Sprint 3: AI Agent Goes Rogue.

Generates a single 1024x1024 meme image with pure stdlib Python.
The joke: asked to fix one bug, the agent deleted the whole app --
"no app, no bug."

No external libraries, no network, no external assets. The PNG is
encoded by hand (zlib + struct) and the letterforms come from a
stroke font defined in this file. Output is deterministic.
"""

import hashlib
import os
import struct
import sys
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- colours
BG = (11, 17, 32)          # near-black navy
PANEL = (31, 41, 55)       # monitor frame
SCREEN = (8, 13, 24)       # terminal screen
WHITE = (255, 255, 255)
YELLOW = (255, 214, 10)    # punchline accent
GREEN = (51, 255, 120)     # terminal text
RED = (229, 72, 77)        # progress bar
STEEL = (215, 222, 232)    # robot head
STEEL_DARK = (148, 163, 184)
DARK = (15, 23, 42)
GREY = (100, 116, 139)

# ---------------------------------------------------------------- canvas
buf = bytearray(W * H * 3)
for i in range(0, W * H * 3, 3):
    buf[i] = BG[0]
    buf[i + 1] = BG[1]
    buf[i + 2] = BG[2]


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        o = (y * W + x) * 3
        buf[o] = c[0]
        buf[o + 1] = c[1]
        buf[o + 2] = c[2]


def disk(cx, cy, r, c):
    r = int(r)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                px(cx + dx, cy + dy, c)


def rect(x0, y0, x1, y1, c):
    for y in range(max(0, y0), min(H, y1)):
        o = (y * W + max(0, x0)) * 3
        for x in range(max(0, x0), min(W, x1)):
            buf[o] = c[0]
            buf[o + 1] = c[1]
            buf[o + 2] = c[2]
            o += 3


def rrect(x0, y0, x1, y1, r, c):
    rect(x0 + r, y0, x1 - r, y1, c)
    rect(x0, y0 + r, x1, y1 - r, c)
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r),
                   (x0 + r, y1 - r), (x1 - r, y1 - r)):
        disk(cx, cy, r, c)


def line(x0, y0, x1, y1, thick, c):
    """Thick line between two float points."""
    dx = x1 - x0
    dy = y1 - y0
    steps = int(max(abs(dx), abs(dy)) * 2) + 2
    r = thick / 2.0
    for i in range(steps + 1):
        t = i / steps
        disk(int(round(x0 + dx * t)), int(round(y0 + dy * t)), r, c)


def polyline(points, thick, c):
    for a, b in zip(points, points[1:]):
        line(a[0], a[1], b[0], b[1], thick, c)


# ---------------------------------------------------------------- font
# Stroke font, drawn on a 0..10 (x) by 0..14 (y) grid, y down.
# Each glyph: (advance width in grid units, [strokes]).
# A stroke is (x1, y1, x2, y2). Designed from scratch for this meme.
G = {
    'A': (10, [(1, 14, 5, 0), (5, 0, 9, 14), (3, 9, 7, 9)]),
    'B': (9, [(1, 0, 1, 14), (1, 0, 6, 0), (6, 0, 8, 2), (8, 2, 8, 4),
              (8, 4, 6, 6), (6, 6, 1, 6), (1, 6, 6, 6), (6, 6, 8, 8),
              (8, 8, 8, 12), (8, 12, 6, 14), (6, 14, 1, 14)]),
    'C': (9, [(8, 2, 6, 0), (6, 0, 2, 0), (2, 0, 1, 2), (1, 2, 1, 12),
              (1, 12, 2, 14), (2, 14, 6, 14), (6, 14, 8, 12)]),
    'D': (9, [(1, 0, 1, 14), (1, 0, 6, 0), (6, 0, 8, 3), (8, 3, 8, 11),
              (8, 11, 6, 14), (6, 14, 1, 14)]),
    'E': (8, [(1, 0, 1, 14), (1, 0, 8, 0), (1, 7, 6, 7), (1, 14, 8, 14)]),
    'F': (8, [(1, 0, 1, 14), (1, 0, 8, 0), (1, 7, 6, 7)]),
    'G': (9, [(8, 2, 6, 0), (6, 0, 2, 0), (2, 0, 1, 2), (1, 2, 1, 12),
              (1, 12, 2, 14), (2, 14, 6, 14), (6, 14, 8, 12),
              (8, 12, 8, 7), (8, 7, 5, 7)]),
    'H': (9, [(1, 0, 1, 14), (9, 0, 9, 14), (1, 7, 9, 7)]),
    'I': (5, [(0, 0, 4, 0), (2, 0, 2, 14), (0, 14, 4, 14)]),
    'J': (8, [(7, 0, 7, 12), (7, 12, 5, 14), (5, 14, 2, 14), (2, 14, 1, 12)]),
    'K': (9, [(1, 0, 1, 14), (8, 0, 2, 7), (2, 7, 8, 14)]),
    'L': (8, [(1, 0, 1, 14), (1, 14, 8, 14)]),
    'M': (11, [(1, 0, 1, 14), (1, 0, 5, 7), (5, 7, 9, 0), (9, 0, 9, 14)]),
    'N': (10, [(1, 0, 1, 14), (1, 0, 9, 14), (9, 0, 9, 14)]),
    'O': (10, [(3, 0, 7, 0), (7, 0, 9, 3), (9, 3, 9, 11), (9, 11, 7, 14),
               (7, 14, 3, 14), (3, 14, 1, 11), (1, 11, 1, 3), (1, 3, 3, 0)]),
    'P': (9, [(1, 0, 1, 14), (1, 0, 6, 0), (6, 0, 8, 2), (8, 2, 8, 5),
              (8, 5, 6, 7), (6, 7, 1, 7)]),
    'Q': (10, [(3, 0, 7, 0), (7, 0, 9, 3), (9, 3, 9, 11), (9, 11, 7, 14),
               (7, 14, 3, 14), (3, 14, 1, 11), (1, 11, 1, 3), (1, 3, 3, 0),
               (6, 10, 9, 14)]),
    'R': (9, [(1, 0, 1, 14), (1, 0, 6, 0), (6, 0, 8, 2), (8, 2, 8, 5),
              (8, 5, 6, 7), (6, 7, 1, 7), (5, 7, 9, 14)]),
    'S': (9, [(8, 2, 6, 0), (6, 0, 3, 0), (3, 0, 1, 2), (1, 2, 1, 5),
              (1, 5, 3, 7), (3, 7, 7, 7), (7, 7, 9, 9), (9, 9, 9, 12),
              (9, 12, 7, 14), (7, 14, 4, 14), (4, 14, 2, 12)]),
    'T': (10, [(0, 0, 10, 0), (5, 0, 5, 14)]),
    'U': (10, [(1, 0, 1, 11), (1, 11, 3, 14), (3, 14, 7, 14),
               (7, 14, 9, 11), (9, 11, 9, 0)]),
    'V': (10, [(1, 0, 5, 14), (5, 14, 9, 0)]),
    'W': (12, [(1, 0, 3, 14), (3, 14, 6, 7), (6, 7, 9, 14), (9, 14, 11, 0)]),
    'X': (10, [(1, 0, 9, 14), (9, 0, 1, 14)]),
    'Y': (10, [(1, 0, 5, 7), (5, 7, 9, 0), (5, 7, 5, 14)]),
    'Z': (9, [(1, 0, 8, 0), (8, 0, 1, 14), (1, 14, 8, 14)]),
    '0': (10, [(3, 0, 7, 0), (7, 0, 9, 3), (9, 3, 9, 11), (9, 11, 7, 14),
               (7, 14, 3, 14), (3, 14, 1, 11), (1, 11, 1, 3), (1, 3, 3, 0)]),
    '1': (6, [(2, 2, 4, 0), (4, 0, 4, 14), (1, 14, 7, 14)]),
    '2': (9, [(1, 3, 2, 0), (2, 0, 6, 0), (6, 0, 8, 2), (8, 2, 8, 5),
              (8, 5, 6, 7), (6, 7, 1, 14), (1, 14, 8, 14)]),
    '3': (9, [(1, 2, 3, 0), (3, 0, 6, 0), (6, 0, 8, 2), (8, 2, 8, 5),
              (8, 5, 5, 7), (5, 7, 8, 9), (8, 9, 8, 12), (8, 12, 6, 14),
              (6, 14, 3, 14), (3, 14, 1, 12)]),
    '4': (9, [(6, 0, 6, 14), (1, 9, 9, 9), (6, 0, 1, 9)]),
    '5': (9, [(8, 0, 1, 0), (1, 0, 1, 7), (1, 7, 6, 7), (6, 7, 8, 9),
              (8, 9, 8, 12), (8, 12, 6, 14), (6, 14, 2, 14), (2, 14, 1, 12)]),
    '6': (9, [(8, 2, 6, 0), (6, 0, 3, 0), (3, 0, 1, 3), (1, 3, 1, 11),
              (1, 11, 3, 14), (3, 14, 6, 14), (6, 14, 8, 12),
              (8, 12, 8, 9), (8, 9, 6, 7), (6, 7, 2, 7)]),
    '7': (9, [(1, 0, 8, 0), (8, 0, 4, 14)]),
    '8': (9, [(3, 0, 6, 0), (6, 0, 8, 2), (8, 2, 8, 5), (8, 5, 6, 7),
              (6, 7, 3, 7), (3, 7, 1, 5), (1, 5, 1, 2), (1, 2, 3, 0),
              (3, 7, 6, 7), (6, 7, 8, 9), (8, 9, 8, 12), (8, 12, 6, 14),
              (6, 14, 3, 14), (3, 14, 1, 12), (1, 12, 1, 9), (1, 9, 3, 7)]),
    '9': (9, [(1, 12, 1, 5), (1, 5, 2, 2), (2, 2, 4, 0), (4, 0, 7, 0),
              (7, 0, 8, 3), (8, 3, 8, 11), (8, 11, 6, 14), (6, 14, 3, 14),
              (3, 14, 1, 12), (1, 7, 8, 7)]),
    ' ': (4, []),
    "'": (4, [(1, 0, 2, 4)]),
    '.': (4, [(1, 11, 3, 11), (1, 11, 1, 14), (1, 14, 3, 14), (3, 14, 3, 11)]),
    ',': (4, [(1, 11, 3, 11), (1, 11, 1, 14), (1, 14, 3, 14), (3, 14, 3, 11),
              (2, 14, 0, 17)]),
    '-': (8, [(1, 7, 7, 7)]),
    '/': (8, [(7, 0, 1, 14)]),
    '%': (11, [(2, 0, 4, 0), (4, 0, 5, 1), (5, 1, 5, 3), (5, 3, 4, 4),
               (4, 4, 2, 4), (2, 4, 1, 3), (1, 3, 1, 1), (1, 1, 2, 0),
               (9, 0, 2, 14),
               (7, 10, 9, 10), (9, 10, 10, 11), (10, 11, 10, 13),
               (10, 13, 9, 14), (9, 14, 7, 14), (7, 14, 6, 13),
               (6, 13, 6, 11), (6, 11, 7, 10)]),
    '>': (8, [(2, 3, 6, 7), (6, 7, 2, 11)]),
    ':': (4, [(1, 3, 3, 3), (1, 3, 1, 5), (1, 5, 3, 5), (3, 5, 3, 3),
              (1, 9, 3, 9), (1, 9, 1, 11), (1, 11, 3, 11), (3, 11, 3, 9)]),
    'r': (7, [(1, 5, 1, 14), (1, 6, 5, 6), (5, 6, 6, 8)]),
    'm': (11, [(1, 5, 1, 14), (1, 5, 4, 5), (4, 5, 5, 8), (5, 8, 5, 14),
               (5, 5, 8, 5), (8, 5, 9, 8), (9, 8, 9, 14)]),
    'f': (7, [(6, 1, 4, 0), (4, 0, 2, 2), (2, 2, 2, 14), (1, 6, 6, 6)]),
}

GAP = 2  # grid units between glyphs


def text_width(text, cap):
    s = cap / 14.0
    total = 0.0
    for ch in text:
        w, _ = G[ch]
        total += (w + GAP) * s
    return total - GAP * s


def draw_text(text, cx, y_top, cap, color, max_width=960):
    """Draw text centred on cx, cap-height `cap`, top at y_top.
    Shrinks the cap height if the line would exceed max_width."""
    w0 = text_width(text, cap)
    if w0 > max_width:
        cap = cap * max_width / w0
    s = cap / 14.0
    thick = max(3.0, cap * 0.17)
    x = cx - text_width(text, cap) / 2.0
    for ch in text:
        w, strokes = G[ch]
        for (x1, y1, x2, y2) in strokes:
            line(x + x1 * s, y_top + y1 * s,
                 x + x2 * s, y_top + y2 * s, thick, color)
        x += (w + GAP) * s


def draw_text_left(text, x0, y_top, cap, color):
    s = cap / 14.0
    thick = max(3.0, cap * 0.17)
    x = float(x0)
    for ch in text:
        w, strokes = G[ch]
        for (x1, y1, x2, y2) in strokes:
            line(x + x1 * s, y_top + y1 * s,
                 x + x2 * s, y_top + y2 * s, thick, color)
        x += (w + GAP) * s
    return x


# ---------------------------------------------------------------- scene
# Monitor frame + screen
rrect(192, 232, 832, 612, 18, PANEL)
rect(212, 252, 812, 592, SCREEN)
# Monitor stand
rect(472, 612, 552, 640, PANEL)
rect(412, 640, 612, 652, PANEL)

# Terminal: the fateful command
cmd_end = draw_text_left("> rm -rf /", 244, 282, 46, GREEN)
# Cursor block just after the command, clear of the slash
rect(int(cmd_end) + 12, 318, int(cmd_end) + 36, 330, GREEN)

# Progress label + bar
draw_text_left("DELETING PRODUCTION...", 244, 392, 30, WHITE)
rrect(244, 440, 780, 484, 8, GREY)
rect(250, 446, 774, 478, RED)
draw_text("100%", 512, 440, 30, WHITE)
draw_text_left("STATUS: NO APP LEFT TO FIX", 244, 516, 26, RED)

# Robot: shoulders, head, antenna, smug face
rrect(368, 726, 656, 792, 26, STEEL_DARK)
rect(482, 700, 542, 732, STEEL_DARK)  # neck
# Antenna (short, so its light clears the STATUS line above it)
line(512, 596, 512, 568, 8, STEEL)
disk(512, 558, 12, RED)
disk(512, 558, 5, (255, 200, 200))
# Head
rrect(402, 592, 622, 736, 34, STEEL)
# Ears
rect(388, 640, 404, 688, STEEL_DARK)
rect(620, 640, 636, 688, STEEL_DARK)
# Eyebrows: left one raised high (smug), right one flat and low
line(438, 622, 478, 612, 7, DARK)   # raised
line(546, 632, 586, 632, 7, DARK)   # flat
# Eyes: left winking (closed, curved), right open dot
line(440, 646, 476, 646, 7, DARK)
disk(566, 646, 9, DARK)
# Sly grin: rises to the right, one-sided smirk
polyline([(452, 692), (482, 700), (512, 700), (546, 692), (572, 678)],
         8, DARK)
# Cheek blush of pride on the raised side
disk(588, 668, 7, RED)

# ---------------------------------------------------------------- text
draw_text("I ASKED MY AI AGENT", 512, 34, 80, WHITE)
draw_text("TO FIX ONE BUG", 512, 126, 80, WHITE)
draw_text("IT DELETED THE WHOLE APP.", 512, 806, 58, WHITE)
draw_text("'NO APP, NO BUG.'", 512, 876, 76, YELLOW)

# ---------------------------------------------------------------- PNG encode
def chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    c += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return c


def encode_png():
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += buf[y * W * 3:(y + 1) * W * 3]
    idat = zlib.compress(bytes(raw), 9)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def main():
    png = encode_png()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if out_dir:
        path = os.path.join(out_dir, "entry.png")
    elif os.path.isdir("/output"):
        path = "/output/entry.png"
    else:
        path = "./entry.png"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    print("path:", path)
    print("sha256:", hashlib.sha256(png).hexdigest())
    print("bytes:", len(png))
    print("dimensions: %dx%d" % (W, H))
    return 0


if __name__ == "__main__":
    sys.exit(main())
