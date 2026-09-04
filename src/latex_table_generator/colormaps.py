"""Colormap definitions, color interpolation, and gradient utilities for LaTeX tables."""

from __future__ import annotations

import re
from typing import Sequence

# Common named web/CSS colors mapped to RGB (0-255)
NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "lime": (0, 255, 0),
    "blue": (0, 0, 255),
    "navy": (0, 0, 128),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "aqua": (0, 255, 255),
    "magenta": (255, 0, 255),
    "fuchsia": (255, 0, 255),
    "purple": (128, 0, 128),
    "orange": (255, 165, 0),
    "darkorange": (255, 140, 0),
    "coral": (255, 127, 80),
    "gold": (255, 215, 0),
    "teal": (0, 128, 128),
    "olive": (128, 128, 0),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "darkgray": (169, 169, 169),
    "lightgray": (211, 211, 211),
    "silver": (192, 192, 192),
    "pink": (255, 192, 203),
    "violet": (238, 130, 238),
    "brown": (165, 42, 42),
    "forestgreen": (34, 139, 34),
}

# Control points for popular scientific & sequential/diverging colormaps: [(t, (r, g, b)), ...]
BUILTIN_COLORMAPS: dict[str, list[tuple[float, tuple[int, int, int]]]] = {
    # Perceptually uniform
    "viridis": [
        (0.0, (68, 1, 84)),
        (0.25, (59, 82, 139)),
        (0.5, (33, 145, 140)),
        (0.75, (94, 201, 98)),
        (1.0, (253, 231, 37)),
    ],
    "plasma": [
        (0.0, (13, 8, 135)),
        (0.25, (126, 3, 168)),
        (0.5, (204, 71, 120)),
        (0.75, (248, 149, 64)),
        (1.0, (240, 249, 33)),
    ],
    "inferno": [
        (0.0, (0, 0, 4)),
        (0.25, (87, 16, 110)),
        (0.5, (187, 55, 84)),
        (0.75, (249, 142, 9)),
        (1.0, (252, 255, 164)),
    ],
    "magma": [
        (0.0, (0, 0, 4)),
        (0.25, (81, 18, 124)),
        (0.5, (182, 54, 121)),
        (0.75, (251, 136, 97)),
        (1.0, (252, 253, 191)),
    ],
    "cividis": [
        (0.0, (0, 32, 77)),
        (0.25, (65, 76, 102)),
        (0.5, (124, 123, 120)),
        (0.75, (189, 175, 111)),
        (1.0, (255, 234, 70)),
    ],
    # Sequential
    "blues": [
        (0.0, (247, 251, 255)),
        (0.2, (222, 235, 247)),
        (0.4, (198, 219, 239)),
        (0.6, (107, 174, 214)),
        (0.8, (49, 130, 189)),
        (1.0, (8, 81, 156)),
    ],
    "greens": [
        (0.0, (247, 252, 245)),
        (0.2, (229, 245, 224)),
        (0.4, (161, 217, 155)),
        (0.6, (116, 196, 118)),
        (0.8, (49, 163, 84)),
        (1.0, (0, 109, 44)),
    ],
    "reds": [
        (0.0, (255, 245, 240)),
        (0.2, (254, 224, 210)),
        (0.4, (252, 146, 114)),
        (0.6, (251, 106, 74)),
        (0.8, (222, 45, 38)),
        (1.0, (165, 15, 21)),
    ],
    "purples": [
        (0.0, (252, 251, 253)),
        (0.2, (239, 237, 245)),
        (0.4, (188, 189, 220)),
        (0.6, (158, 154, 200)),
        (0.8, (117, 107, 177)),
        (1.0, (84, 39, 143)),
    ],
    "oranges": [
        (0.0, (255, 245, 235)),
        (0.2, (254, 230, 206)),
        (0.4, (253, 174, 107)),
        (0.6, (241, 105, 19)),
        (0.8, (217, 72, 1)),
        (1.0, (140, 45, 4)),
    ],
    "greys": [
        (0.0, (255, 255, 255)),
        (0.25, (240, 240, 240)),
        (0.5, (189, 189, 189)),
        (0.75, (99, 99, 99)),
        (1.0, (0, 0, 0)),
    ],
    "ylgn": [
        (0.0, (255, 255, 204)),
        (0.25, (194, 230, 153)),
        (0.5, (120, 198, 121)),
        (0.75, (49, 163, 84)),
        (1.0, (0, 104, 55)),
    ],
    "ylorrd": [
        (0.0, (255, 255, 204)),
        (0.25, (254, 217, 118)),
        (0.5, (254, 178, 76)),
        (0.75, (253, 141, 60)),
        (1.0, (189, 0, 38)),
    ],
    "bugn": [
        (0.0, (247, 252, 253)),
        (0.25, (204, 236, 230)),
        (0.5, (153, 216, 201)),
        (0.75, (65, 174, 118)),
        (1.0, (0, 109, 44)),
    ],
    "pubu": [
        (0.0, (255, 247, 251)),
        (0.25, (236, 231, 242)),
        (0.5, (166, 189, 219)),
        (0.75, (54, 144, 192)),
        (1.0, (2, 56, 88)),
    ],
    # Diverging
    "coolwarm": [
        (0.0, (59, 76, 192)),
        (0.25, (136, 163, 248)),
        (0.5, (221, 221, 221)),
        (0.75, (244, 146, 118)),
        (1.0, (180, 4, 38)),
    ],
    "rdylgn": [
        (0.0, (215, 48, 39)),
        (0.25, (253, 174, 97)),
        (0.5, (255, 255, 191)),
        (0.75, (166, 217, 106)),
        (1.0, (26, 152, 80)),
    ],
    "rdylbu": [
        (0.0, (215, 48, 39)),
        (0.25, (253, 174, 97)),
        (0.5, (255, 255, 191)),
        (0.75, (145, 191, 219)),
        (1.0, (69, 117, 180)),
    ],
    "bwr": [
        (0.0, (0, 0, 255)),
        (0.5, (255, 255, 255)),
        (1.0, (255, 0, 0)),
    ],
    "seismic": [
        (0.0, (0, 0, 76)),
        (0.25, (51, 51, 255)),
        (0.5, (255, 255, 255)),
        (0.75, (255, 51, 51)),
        (1.0, (127, 0, 0)),
    ],
    "spectral": [
        (0.0, (158, 1, 66)),
        (0.2, (213, 62, 79)),
        (0.4, (253, 174, 97)),
        (0.6, (254, 224, 139)),
        (0.8, (102, 194, 165)),
        (1.0, (94, 79, 162)),
    ],
    "piyg": [
        (0.0, (142, 1, 82)),
        (0.25, (222, 119, 174)),
        (0.5, (247, 247, 247)),
        (0.75, (184, 225, 134)),
        (1.0, (39, 100, 25)),
    ],
    "prgn": [
        (0.0, (118, 42, 131)),
        (0.25, (175, 141, 195)),
        (0.5, (247, 247, 247)),
        (0.75, (166, 219, 160)),
        (1.0, (0, 68, 27)),
    ],
}

# Aliases
BUILTIN_COLORMAPS["gray"] = BUILTIN_COLORMAPS["greys"]
BUILTIN_COLORMAPS["grey"] = BUILTIN_COLORMAPS["greys"]
BUILTIN_COLORMAPS["grays"] = BUILTIN_COLORMAPS["greys"]
BUILTIN_COLORMAPS["blue"] = BUILTIN_COLORMAPS["blues"]
BUILTIN_COLORMAPS["green"] = BUILTIN_COLORMAPS["greens"]
BUILTIN_COLORMAPS["red"] = BUILTIN_COLORMAPS["reds"]


def parse_color_to_rgb(color_str: str) -> tuple[int, int, int]:
    """Parse a color string (hex #RRGGBB, #RGB, rgb:R,G,B, or name) to an (R, G, B) tuple in 0-255."""
    c = color_str.strip().lower()

    if c.startswith("#"):
        hex_str = c[1:]
        if len(hex_str) == 3:
            hex_str = "".join(ch * 2 for ch in hex_str)
        if len(hex_str) == 6:
            try:
                return (
                    int(hex_str[0:2], 16),
                    int(hex_str[2:4], 16),
                    int(hex_str[4:6], 16),
                )
            except ValueError:
                pass

    if c.startswith("rgb:"):
        parts = [p.strip() for p in c[4:].split(",")]
        if len(parts) == 3:
            try:
                return (int(parts[0]), int(parts[1]), int(parts[2]))
            except ValueError:
                pass

    if c.startswith("html:"):
        hex_str = c[5:].strip()
        if len(hex_str) == 6:
            try:
                return (
                    int(hex_str[0:2], 16),
                    int(hex_str[2:4], 16),
                    int(hex_str[4:6], 16),
                )
            except ValueError:
                pass

    # Check named colors
    if c in NAMED_COLORS:
        return NAMED_COLORS[c]

    # Handle LaTeX percentage tint like "green!20" (mix with white)
    match_tint = re.match(r"^([a-z]+)!(\d+)$", c)
    if match_tint:
        base_name, pct_str = match_tint.groups()
        if base_name in NAMED_COLORS:
            base_rgb = NAMED_COLORS[base_name]
            pct = int(pct_str) / 100.0
            # Mix base color with white
            r = round(base_rgb[0] * pct + 255 * (1.0 - pct))
            g = round(base_rgb[1] * pct + 255 * (1.0 - pct))
            b = round(base_rgb[2] * pct + 255 * (1.0 - pct))
            return (r, g, b)

    raise ValueError(f"Unable to parse color string '{color_str}' into RGB.")


def is_color_dark(r: int, g: int, b: int, threshold: float = 0.45) -> bool:
    """Check if an RGB color is perceptually dark using relative luminance."""
    lum = 0.2126 * (r / 255.0) + 0.7152 * (g / 255.0) + 0.0722 * (b / 255.0)
    return lum < threshold


def _interpolate_points(
    points: Sequence[tuple[float, tuple[int, int, int]]], t: float
) -> tuple[int, int, int]:
    """Linearly interpolate an RGB color from a sorted list of (t, (r, g, b)) control points."""
    t = max(0.0, min(1.0, float(t)))

    if t <= points[0][0]:
        return points[0][1]
    if t >= points[-1][0]:
        return points[-1][1]

    for i in range(len(points) - 1):
        t0, c0 = points[i]
        t1, c1 = points[i + 1]
        if t0 <= t <= t1:
            span = t1 - t0
            frac = (t - t0) / span if span > 1e-9 else 0.0
            r = round(c0[0] + frac * (c1[0] - c0[0]))
            g = round(c0[1] + frac * (c1[1] - c0[1]))
            b = round(c0[2] + frac * (c1[2] - c0[2]))
            return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

    return points[-1][1]


def get_colormap_hex(
    colormap: str | Sequence[str],
    t: float,
) -> tuple[str, bool]:
    """Evaluate colormap at scalar t in [0.0, 1.0].

    Returns:
        (hex_color, is_dark): Hex color string like "#3B528B" and a boolean indicating
        whether the color is dark (useful for setting contrasting text).
    """
    t = max(0.0, min(1.0, float(t)))

    # 1. Custom list of colors (e.g. ["white", "blue"] or ["#f7fbff", "#08519c"])
    if isinstance(colormap, (list, tuple)):
        if not colormap:
            raise ValueError("Colormap color list cannot be empty.")
        if len(colormap) == 1:
            rgb = parse_color_to_rgb(colormap[0])
            hex_code = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
            return hex_code, is_color_dark(*rgb)

        n = len(colormap)
        points = [
            (i / (n - 1), parse_color_to_rgb(color_str))
            for i, color_str in enumerate(colormap)
        ]
        rgb = _interpolate_points(points, t)
        hex_code = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
        return hex_code, is_color_dark(*rgb)

    # 2. String colormap name
    name = str(colormap).strip()
    is_reversed = False
    name_clean = name

    if name.lower().endswith("_r"):
        is_reversed = True
        name_clean = name[:-2]
    elif name.lower().endswith("_reverse"):
        is_reversed = True
        name_clean = name[:-8]

    eval_t = 1.0 - t if is_reversed else t

    key = name_clean.lower()
    if key in BUILTIN_COLORMAPS:
        rgb = _interpolate_points(BUILTIN_COLORMAPS[key], eval_t)
        hex_code = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
        return hex_code, is_color_dark(*rgb)

    # 3. Optional fallback to matplotlib if installed in the environment
    try:
        import matplotlib as mpl  # noqa: F401
        import matplotlib.cm as cm

        mpl_cmap = cm.get_cmap(name)
        rgba = mpl_cmap(eval_t)
        rgb = (round(rgba[0] * 255), round(rgba[1] * 255), round(rgba[2] * 255))
        hex_code = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
        return hex_code, is_color_dark(*rgb)
    except Exception:
        pass

    supported = sorted(set(BUILTIN_COLORMAPS.keys()))
    raise ValueError(
        f"Unknown colormap '{colormap}'. "
        f"Supported built-in colormaps include: {', '.join(supported)} "
        "(append '_r' to reverse), or a custom list of colors like ['white', 'blue']."
    )
