"""Pure point geometry for turning fiducial centroids into an ordered quad.

No image data here -- just coordinates. Three jobs:

  * reconstruct a missing 4th corner from 3 (``complete_rectangle``),
  * reduce a cloud of candidate points to the 4 outer corners
    (``select_corner_quad``), and
  * put 4 corners into a known order for the perspective transform
    (``order_clockwise`` + ``template_src_points``).

Image coordinates are used throughout: x grows right, y grows DOWN.
"""
from __future__ import annotations

import itertools

import cv2
import numpy as np

# How tightly a convex-hull-reduced polygon must match 4 (or 3) vertices. These
# epsilons are fractions of the hull perimeter passed to approxPolyDP, tried
# small-to-large so the tightest fit that yields 4 (then 3) corners wins.
_APPROX_EPSILONS = (0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.12)


def complete_rectangle(points: list) -> list:
    """Reconstruct a 4th rectangle corner from 3 (parallelogram completion).

    Given three corners of a rectangle, the two that are farthest apart are the
    diagonal (opposite corners); the remaining point is the third corner, and
    the 4th is its mirror across the diagonal's midpoint::

        p ---- ?        p and q are the diagonal (farthest-apart pair);
        |      |        r is the third given corner;
        r ---- q        the missing corner is p + q - r.

    Returns the four corners as ``[p, q, r, p+q-r]`` (order not canonical;
    ``order_clockwise`` sorts them afterwards).
    """
    # The farthest-apart pair of the three points is the diagonal.
    i, j = max(
        itertools.combinations(range(3), 2),
        key=lambda pair: (points[pair[0]][0] - points[pair[1]][0]) ** 2
        + (points[pair[0]][1] - points[pair[1]][1]) ** 2,
    )
    k = ({0, 1, 2} - {i, j}).pop()
    px, py = points[i]
    qx, qy = points[j]
    rx, ry = points[k]
    fourth = [px + qx - rx, py + qy - ry]
    return [list(points[i]), list(points[j]), list(points[k]), fourth]


def select_corner_quad(points: list) -> list | None:
    """Pick the 4 fiducial corners from a cloud of candidate points.

    The real fiducials are the *outermost* points, so interior strays (a filled
    mark, a smudge mistaken for a square) never lie on the convex hull and cannot
    displace a true corner. The hull is then reduced to its dominant vertices:

      * 4 vertices -> the four fiducials, used directly;
      * 3 vertices -> a torn / occluded corner, so reconstruct the 4th;
      * otherwise  -> fall back to the largest-area convex quad among the hull
        vertices.

    Returns a list of 4 ``[x, y]`` corners, or ``None`` if fewer than 3 points
    were given.
    """
    count = len(points)
    if count < 3:
        return None
    if count == 3:
        return complete_rectangle(points)

    hull = cv2.convexHull(np.array(points, dtype=np.float32))
    perimeter = cv2.arcLength(hull, True)

    # Try progressively looser polygon approximations; keep the first that lands
    # on exactly 4 vertices (preferred) or 3 (reconstruct the 4th).
    approx_four = None
    approx_three = None
    for epsilon in _APPROX_EPSILONS:
        approx = cv2.approxPolyDP(hull, epsilon * perimeter, True).reshape(-1, 2)
        if len(approx) == 4 and approx_four is None:
            approx_four = approx
        elif len(approx) == 3 and approx_three is None:
            approx_three = approx

    if approx_four is not None:
        return [[float(p[0]), float(p[1])] for p in approx_four]
    if approx_three is not None:
        return complete_rectangle([[float(p[0]), float(p[1])] for p in approx_three])

    # Fallback: the largest-area convex quad among the hull vertices themselves.
    hull_points = [[float(p[0]), float(p[1])] for p in hull.reshape(-1, 2)]
    if len(hull_points) < 3:
        return None
    if len(hull_points) == 3:
        return complete_rectangle(hull_points)

    best_quad = None
    best_area = -1.0
    for combo in itertools.combinations(range(len(hull_points)), 4):
        polygon = np.array([hull_points[i] for i in combo], dtype=np.float32)
        area = cv2.contourArea(cv2.convexHull(polygon))
        if area > best_area:
            best_area = area
            best_quad = [hull_points[i] for i in combo]
    return best_quad


def order_clockwise(quad: list) -> np.ndarray:
    """Order 4 points clockwise around their centroid (image coords, y down).

    ``atan2(dy, dx)`` gives each corner's angle from the centroid; sorting by
    that angle walks the corners in order. Because y grows downward, increasing
    angle traverses them clockwise on screen. The starting vertex is arbitrary --
    the caller tries all four cyclic starts to resolve orientation.
    """
    pts = np.array(quad, dtype=np.float64)
    centroid = pts.mean(axis=0)
    angles = np.arctan2(pts[:, 1] - centroid[1], pts[:, 0] - centroid[0])
    return pts[np.argsort(angles)]


def template_src_points(clockwise: np.ndarray, rotation: int) -> np.ndarray:
    """Source points in template order (TL, TR, BL, BR) for a cyclic rotation.

    A clockwise walk from the top-left visits TL, TR, BR, BL. The perspective
    transform wants template order TL, TR, BL, BR, so the last two are swapped.
    ``rotation`` (0..3) rolls the starting corner, which is how the four possible
    page orientations (0/90/180/270 deg) are tried::

        clockwise = [TL, TR, BR, BL]   (roll by -rotation to re-label the start)
        returned  = [TL, TR, BL, BR]   (template order)
    """
    rolled = np.roll(clockwise, -rotation, axis=0)
    return np.array([rolled[0], rolled[1], rolled[3], rolled[2]], dtype=np.float32)
