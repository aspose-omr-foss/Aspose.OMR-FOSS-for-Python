"""Image-degradation library for the robustness tests.

Each function takes the clean filled sheet (BGR uint8, cv2 convention) and returns a
degraded BGR image that a real scanner / phone camera / rough handling would produce.
Every degradation is designed to leave the *answer marks and the registration
fiducials legible* -- so demanding 100% recovery is a fair, well-defined bar:

  * rotations (90/180/270 exact, plus small skews like +15, -12)   -> orientation + de-skew
  * angled "phone shot" on a background with perspective + lighting -> perspective registration
  * scanner banding (horizontal/vertical lines)                     -> line-robust sampling
  * handling damage: smudges, scribbles, a torn corner             -> noise + missing-fiducial

Damage (smudges / scribbles / tear) is kept out of the bubble ROIs and, except for the
single torn fiducial, out of the reference marks -- using the descriptor geometry -- so
the ground-truth answers never change.
"""
from __future__ import annotations

import cv2
import numpy as np

from omr._internal import geometry

_WHITE = (255, 255, 255)


# ── helpers ───────────────────────────────────────────────────────────────────

def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def bubble_mask(img_shape, descriptor: dict, inflate: float = 1.8) -> np.ndarray:
    """A uint8 mask (255 where a bubble ROI is, inflated) so damage can avoid marks."""
    h, w = img_shape[:2]
    mask = np.zeros((h, w), np.uint8)
    page = descriptor["Pages"][0]
    for e in page["Elements"]:
        for f in e["Fields"]:
            for b in f["Bubbles"]:
                x, y, bw, bh = b["Box"]
                cx, cy = x + bw / 2, y + bh / 2
                rx, ry = bw * inflate / 2, bh * inflate / 2
                cv2.rectangle(mask, (int(cx - rx), int(cy - ry)),
                              (int(cx + rx), int(cy + ry)), 255, -1)
    # keep the reference marks + rotation marker out of bounds for damage too
    for cx, cy in page["ReferenceCenters"]:
        cv2.rectangle(mask, (int(cx - 90), int(cy - 90)), (int(cx + 90), int(cy + 90)), 255, -1)
    if page.get("RotationMarker"):
        x, y, rw, rh = page["RotationMarker"]
        cv2.rectangle(mask, (int(x - 60), int(y - 60)), (int(x + rw + 60), int(y + rh + 60)), 255, -1)
    return mask


# ── rotations ─────────────────────────────────────────────────────────────────

def rotate_exact(img: np.ndarray, quarter_turns: int) -> np.ndarray:
    """Exact 90 * quarter_turns rotation (1->90 CW, 2->180, 3->270)."""
    codes = {1: cv2.ROTATE_90_CLOCKWISE, 2: cv2.ROTATE_180, 3: cv2.ROTATE_90_COUNTERCLOCKWISE}
    return cv2.rotate(img, codes[quarter_turns % 4]) if quarter_turns % 4 else img.copy()


def rotate_skew(img: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate by an arbitrary angle on an expanded white canvas (no fiducial clipped)."""
    h, w = img.shape[:2]
    c = (w / 2.0, h / 2.0)
    M = cv2.getRotationMatrix2D(c, angle_deg, 1.0)
    cos, sin = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    M[0, 2] += (nw - w) / 2.0
    M[1, 2] += (nh - h) / 2.0
    return cv2.warpAffine(img, M, (nw, nh), flags=cv2.INTER_LINEAR,
                          borderValue=_WHITE)


# ── angled phone shot ─────────────────────────────────────────────────────────

def _wood_background(h: int, w: int, seed: int) -> np.ndarray:
    """A smooth, textured, square-free background (desk surface) for a photo."""
    rng = _rng(seed)
    base = np.linspace(150, 110, w, dtype=np.float32)[None, :].repeat(h, axis=0)
    base += np.linspace(-15, 15, h, dtype=np.float32)[:, None]
    grain = cv2.GaussianBlur(rng.normal(0, 12, (h, w)).astype(np.float32), (0, 0), 3)
    img = np.clip(base + grain, 40, 210).astype(np.uint8)
    bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    bgr[..., 0] = np.clip(bgr[..., 0].astype(int) - 18, 0, 255)   # warmer (less blue)
    bgr[..., 2] = np.clip(bgr[..., 2].astype(int) + 12, 0, 255)
    return bgr


def perspective_phone(img: np.ndarray, seed: int = 7, strength: float = 1.0) -> np.ndarray:
    """Simulate a hand-held phone photo: the sheet lies on a desk, shot from an angle
    (perspective), under uneven lighting, with mild blur + sensor noise. ``strength``
    scales the keystone/tilt (1.0 is a firm angle; higher is more oblique)."""
    h, w = img.shape[:2]
    scale = 1500.0 / h
    sheet = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    sh, sw = sheet.shape[:2]
    cw, ch = int(sw * 1.5), int(sh * 1.35)
    canvas = _wood_background(ch, cw, seed)

    # destination quad for the sheet corners: a tilted, keystoned placement.
    ox, oy = (cw - sw) // 2, (ch - sh) // 2
    dx = sw * 0.14 * strength   # horizontal keystone
    dy = sh * 0.07 * strength   # vertical skew
    src = np.float32([[0, 0], [sw, 0], [sw, sh], [0, sh]])
    dst = np.float32([
        [ox + dx, oy + dy * 0.3],
        [ox + sw - dx * 0.4, oy - dy * 0.2],
        [ox + sw + dx * 0.2, oy + sh - dy],
        [ox - dx * 0.3, oy + sh + dy * 0.6],
    ])
    Hm = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(sheet, Hm, (cw, ch), borderValue=(0, 0, 0))
    mask = cv2.warpPerspective(np.full((sh, sw), 255, np.uint8), Hm, (cw, ch))
    out = canvas.copy()
    out[mask > 0] = warped[mask > 0]

    # uneven lighting: a soft bright spot (position varies with seed) + vignette.
    rng_l = _rng(seed + 5)
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    gx, gy = cw * float(rng_l.uniform(0.2, 0.8)), ch * float(rng_l.uniform(0.2, 0.8))
    light = 1.0 + 0.35 * np.exp(-(((xx - gx) ** 2) / (2 * (cw * 0.5) ** 2) +
                                  ((yy - gy) ** 2) / (2 * (ch * 0.5) ** 2)))
    light -= 0.25 * (((xx - cw / 2) ** 2 + (yy - ch / 2) ** 2) /
                     ((cw / 2) ** 2 + (ch / 2) ** 2))
    out = np.clip(out.astype(np.float32) * light[..., None], 0, 255).astype(np.uint8)

    out = cv2.GaussianBlur(out, (3, 3), 0)
    rng = _rng(seed + 1)
    out = np.clip(out.astype(np.int16) + rng.normal(0, 4, out.shape).astype(np.int16),
                  0, 255).astype(np.uint8)
    return out


# ── scanner banding ───────────────────────────────────────────────────────────

def scanner_lines(img: np.ndarray, seed: int = 3) -> np.ndarray:
    """Add horizontal banding + a few vertical streaks, as from a dirty/failing scanner."""
    out = img.copy()
    h, w = out.shape[:2]
    rng = _rng(seed)
    # periodic horizontal banding
    for y in range(0, h, 15):
        val = int(rng.integers(70, 120))
        thick = int(rng.integers(1, 3))
        cv2.line(out, (0, y), (w, y), (val, val, val), thick)
    # a handful of darker vertical streaks (roller dirt)
    for _ in range(7):
        x = int(rng.integers(0, w))
        val = int(rng.integers(60, 110))
        thick = int(rng.integers(1, 4))
        cv2.line(out, (x, 0), (x, h), (val, val, val), thick)
    return out


# ── handling damage ───────────────────────────────────────────────────────────

def smudges_scribbles(img: np.ndarray, descriptor: dict, seed: int = 11) -> np.ndarray:
    """Real-handling damage: translucent coffee-ring/finger smudges, dark pen scribbles,
    and small stray pen dabs. Damage is placed only where it does not touch an answer
    bubble's sampling ROI or a reference mark -- including in the gaps *between* bubbles
    and across decorative content -- so the ground-truth answers never change. (Damage
    landing directly on an answer mark is deliberately excluded: it would change what a
    human reads too, so exact recovery is not a defined target there.)

    The protected margin (``inflate``) is only modestly larger than a bubble, so strokes
    and dabs routinely pass close to bubbles -- exercising the classifier's robustness to
    nearby ink -- while the 18% sampling inset keeps them out of the measured ROI."""
    out = img.copy()
    h, w = out.shape[:2]
    forbidden = bubble_mask(out.shape, descriptor, inflate=1.35)
    rng = _rng(seed)

    def clear(x0, y0, x1, y1) -> bool:
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        if x1 <= x0 or y1 <= y0:
            return False
        return forbidden[y0:y1, x0:x1].max() == 0

    placed_smudge = placed_scribble = placed_dab = 0
    tries = 0
    while (placed_smudge < 6 or placed_scribble < 6 or placed_dab < 10) and tries < 9000:
        tries += 1
        cx, cy = int(rng.integers(50, w - 50)), int(rng.integers(240, h - 50))
        if placed_smudge < 6:
            rx, ry = int(rng.integers(45, 150)), int(rng.integers(30, 110))
            if clear(cx - rx, cy - ry, cx + rx, cy + ry):
                overlay = out.copy()
                shade = int(rng.integers(80, 160))
                cv2.ellipse(overlay, (cx, cy), (rx, ry), int(rng.integers(0, 180)),
                            0, 360, (shade, shade, shade), -1)
                if rng.random() < 0.4:  # some are hollow coffee rings
                    cv2.ellipse(overlay, (cx, cy), (max(4, rx - 14), max(4, ry - 14)),
                                int(rng.integers(0, 180)), 0, 360, (255, 255, 255), -1)
                a = float(rng.uniform(0.3, 0.6))
                cv2.addWeighted(overlay, a, out, 1 - a, 0, out)
                placed_smudge += 1
                continue
        if placed_scribble < 6:
            rx, ry = int(rng.integers(70, 190)), int(rng.integers(30, 110))
            if clear(cx - rx, cy - ry, cx + rx, cy + ry):
                pts = np.array([[cx + int(rng.integers(-rx, rx)),
                                 cy + int(rng.integers(-ry, ry))] for _ in range(8)], np.int32)
                cv2.polylines(out, [pts], False, (int(rng.integers(15, 60)),) * 3,
                              int(rng.integers(2, 6)))
                placed_scribble += 1
                continue
        if placed_dab < 10:  # small stray pen dabs, often in the gaps between bubbles
            r = int(rng.integers(3, 9))
            if clear(cx - r, cy - r, cx + r, cy + r):
                cv2.circle(out, (cx, cy), r, (int(rng.integers(15, 55)),) * 3, -1)
                placed_dab += 1
    return out


def torn_corner(img: np.ndarray, descriptor: dict, corner: str = "br",
                seed: int = 5) -> np.ndarray:
    """Tear off one paper corner, destroying exactly ONE reference fiducial (the other
    three + the rotation marker survive, so registration must reconstruct the 4th)."""
    out = img.copy()
    h, w = out.shape[:2]
    rng = _rng(seed)
    cut = int(min(h, w) * 0.11)
    jig = lambda: int(rng.integers(-22, 22))  # ragged edge  # noqa: E731
    if corner == "br":
        poly = np.array([[w, h - cut + jig()], [w - cut + jig(), h], [w, h]], np.int32)
    elif corner == "bl":
        poly = np.array([[0, h - cut + jig()], [cut + jig(), h], [0, h]], np.int32)
    elif corner == "tr":
        poly = np.array([[w, cut + jig()], [w - cut + jig(), 0], [w, 0]], np.int32)
    else:  # tl
        poly = np.array([[0, cut + jig()], [cut + jig(), 0], [0, 0]], np.int32)
    # the torn-away region shows the (darker) surface underneath, with a ragged light edge
    cv2.fillPoly(out, [poly], (120, 120, 120))
    cv2.polylines(out, [poly], True, (90, 90, 90), 3)
    return out


def combined(img: np.ndarray, descriptor: dict, seed: int = 21) -> np.ndarray:
    """A realistic worst-case: a skewed scan with scanner banding and a smudge."""
    step1 = smudges_scribbles(img, descriptor, seed=seed)
    step2 = scanner_lines(step1, seed=seed + 1)
    step3 = rotate_skew(step2, -9.0)
    return step3


# ── the registry the tests + demo iterate over ───────────────────────────────

def all_distortions(descriptor: dict) -> dict:
    """name -> callable(clean_bgr) -> degraded_bgr."""
    return {
        "rotate_090": lambda im: rotate_exact(im, 1),
        "rotate_180": lambda im: rotate_exact(im, 2),
        "rotate_270": lambda im: rotate_exact(im, 3),
        "skew_+15": lambda im: rotate_skew(im, 15.0),
        "skew_-12": lambda im: rotate_skew(im, -12.0),
        "skew_+6": lambda im: rotate_skew(im, 6.0),
        "phone_shot": lambda im: perspective_phone(im),
        "scanner_lines": lambda im: scanner_lines(im),
        "smudges_scribbles": lambda im: smudges_scribbles(im, descriptor),
        "torn_corner_br": lambda im: torn_corner(im, descriptor, "br"),
        "torn_corner_tl": lambda im: torn_corner(im, descriptor, "tl"),
        "combined": lambda im: combined(im, descriptor),
    }
