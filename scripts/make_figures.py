#!/usr/bin/env python3
"""Make simple PNG charts using only Python's standard library."""

from __future__ import annotations

import csv
import math
import struct
import zlib
import argparse
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "pipeline_validation"
DEFAULT_FIGURE_DIR = ROOT / "figures" / "pipeline_validation"

W, H = 1100, 720
BG = (255, 255, 255)
INK = (31, 41, 55)
GRID = (229, 231, 235)
COLORS = [(41, 123, 181), (230, 126, 34), (52, 152, 104), (155, 89, 182), (192, 57, 43), (77, 171, 247), (126, 87, 194)]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def png_write(path: Path, width: int, height: int, pixels: bytearray) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw.extend(pixels[y * stride:(y + 1) * stride])
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    data += chunk(b"IEND", b"")
    path.write_bytes(data)


def canvas() -> bytearray:
    return bytearray(BG * (W * H))


def rect(pix: bytearray, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
    x0, x1 = max(0, min(x0, W)), max(0, min(x1, W))
    y0, y1 = max(0, min(y0, H)), max(0, min(y1, H))
    for y in range(y0, y1):
        base = (y * W + x0) * 3
        for _ in range(x0, x1):
            pix[base:base + 3] = bytes(color)
            base += 3


FONT = {
    "A": ["01110","10001","10001","11111","10001","10001","10001"], "B": ["11110","10001","10001","11110","10001","10001","11110"],
    "C": ["01111","10000","10000","10000","10000","10000","01111"], "D": ["11110","10001","10001","10001","10001","10001","11110"],
    "E": ["11111","10000","10000","11110","10000","10000","11111"], "F": ["11111","10000","10000","11110","10000","10000","10000"],
    "G": ["01111","10000","10000","10011","10001","10001","01111"], "H": ["10001","10001","10001","11111","10001","10001","10001"],
    "I": ["11111","00100","00100","00100","00100","00100","11111"], "J": ["00111","00010","00010","00010","10010","10010","01100"],
    "K": ["10001","10010","10100","11000","10100","10010","10001"], "L": ["10000","10000","10000","10000","10000","10000","11111"],
    "M": ["10001","11011","10101","10101","10001","10001","10001"], "N": ["10001","11001","10101","10011","10001","10001","10001"],
    "O": ["01110","10001","10001","10001","10001","10001","01110"], "P": ["11110","10001","10001","11110","10000","10000","10000"],
    "Q": ["01110","10001","10001","10001","10101","10010","01101"], "R": ["11110","10001","10001","11110","10100","10010","10001"],
    "S": ["01111","10000","10000","01110","00001","00001","11110"], "T": ["11111","00100","00100","00100","00100","00100","00100"],
    "U": ["10001","10001","10001","10001","10001","10001","01110"], "V": ["10001","10001","10001","10001","10001","01010","00100"],
    "W": ["10001","10001","10001","10101","10101","10101","01010"], "X": ["10001","01010","00100","00100","00100","01010","10001"],
    "Y": ["10001","01010","00100","00100","00100","00100","00100"], "Z": ["11111","00001","00010","00100","01000","10000","11111"],
    "0": ["01110","10001","10011","10101","11001","10001","01110"], "1": ["00100","01100","00100","00100","00100","00100","01110"],
    "2": ["01110","10001","00001","00010","00100","01000","11111"], "3": ["11110","00001","00001","01110","00001","00001","11110"],
    "4": ["00010","00110","01010","10010","11111","00010","00010"], "5": ["11111","10000","10000","11110","00001","00001","11110"],
    "6": ["01110","10000","10000","11110","10001","10001","01110"], "7": ["11111","00001","00010","00100","01000","01000","01000"],
    "8": ["01110","10001","10001","01110","10001","10001","01110"], "9": ["01110","10001","10001","01111","00001","00001","01110"],
    " ": ["00000","00000","00000","00000","00000","00000","00000"], "-": ["00000","00000","00000","11111","00000","00000","00000"],
    "/": ["00001","00010","00010","00100","01000","01000","10000"], ".": ["00000","00000","00000","00000","00000","01100","01100"],
    "%": ["11001","11010","00100","01000","10110","00110","00000"], ":": ["00000","01100","01100","00000","01100","01100","00000"],
}


def text(pix: bytearray, x: int, y: int, s: str, scale: int = 3, color: tuple[int, int, int] = INK) -> None:
    cx = x
    for ch in s.upper():
        glyph = FONT.get(ch, FONT[" "])
        for gy, row in enumerate(glyph):
            for gx, val in enumerate(row):
                if val == "1":
                    rect(pix, cx + gx * scale, y + gy * scale, cx + (gx + 1) * scale, y + (gy + 1) * scale, color)
        cx += 6 * scale


def axes(pix: bytearray, title: str, ymax: float = 1.0) -> None:
    text(pix, 70, 35, title, 4)
    left, top, right, bottom = 105, 115, 1040, 600
    rect(pix, left, bottom, right, bottom + 3, INK)
    rect(pix, left, top, left + 3, bottom, INK)
    for i in range(1, 5):
        y = bottom - int((bottom - top) * i / 5)
        rect(pix, left, y, right, y + 1, GRID)
        text(pix, 40, y - 10, f"{int(ymax * i / 5 * 100)}%", 2, (75, 85, 99))


def grouped_bar(path: Path, title: str, categories: list[str], groups: list[str], values: dict[tuple[str, str], float]) -> None:
    pix = canvas()
    axes(pix, title)
    left, top, right, bottom = 125, 115, 1025, 600
    slot = (right - left) / len(categories)
    barw = max(10, int(slot / (len(groups) + 1.8)))
    for ci, cat in enumerate(categories):
        start = int(left + ci * slot + barw * 0.5)
        for gi, group in enumerate(groups):
            val = values.get((cat, group), 0.0)
            h = int((bottom - top) * val)
            x0 = start + gi * barw
            rect(pix, x0, bottom - h, x0 + barw - 4, bottom, COLORS[gi % len(COLORS)])
            text(pix, x0, bottom - h - 24, f"{int(round(val * 100))}", 2, COLORS[gi % len(COLORS)])
        label = cat[:15].replace("_", " ")
        text(pix, int(left + ci * slot), 625, label, 2)
    for gi, group in enumerate(groups):
        x = 720 + gi * 145
        rect(pix, x, 70, x + 24, 94, COLORS[gi % len(COLORS)])
        text(pix, x + 34, 72, group.replace("_", " "), 2)
    png_write(path, W, H, pix)


def simple_bar(path: Path, title: str, labels: list[str], vals: list[float]) -> None:
    pix = canvas()
    axes(pix, title)
    left, top, right, bottom = 135, 115, 1015, 600
    slot = (right - left) / len(labels)
    for i, (label, val) in enumerate(zip(labels, vals)):
        h = int((bottom - top) * val)
        x0 = int(left + i * slot + slot * 0.18)
        x1 = int(left + (i + 1) * slot - slot * 0.18)
        rect(pix, x0, bottom - h, x1, bottom, COLORS[i % len(COLORS)])
        text(pix, x0 + 10, bottom - h - 28, f"{val * 100:.1f}%", 2)
        text(pix, x0, 625, label.replace("_", " ")[:16], 2)
    png_write(path, W, H, pix)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Make PNG charts.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--figure-dir", default=str(DEFAULT_FIGURE_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    figure_dir = Path(args.figure_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)
    rows = read_csv(output_dir / "feasibility_scores.csv")

    modes = sorted({r["transportation_mode"] for r in rows})
    mode_values = {}
    for condition in ["baseline", "spatial_grounded"]:
        subset = [r for r in rows if r["condition"] == condition]
        counts = Counter(r["transportation_mode"] for r in subset)
        for mode in modes:
            mode_values[(mode, condition)] = counts[mode] / len(subset)
    grouped_bar(figure_dir / "transportation_mode_distribution.png", "Transportation Mode Distribution", modes, ["baseline", "spatial_grounded"], mode_values)

    labels = []
    vals = []
    for condition in ["baseline", "spatial_grounded"]:
        for vehicle in ["Yes", "No"]:
            subset = [r for r in rows if r["condition"] == condition and r["vehicle_access"] == vehicle]
            labels.append(f"{condition}_{vehicle}")
            vals.append(sum(float(r["any_violation"]) for r in subset) / len(subset) if subset else 0.0)
    simple_bar(figure_dir / "violation_by_vehicle_access.png", "Violation Rate By Vehicle Access", labels, vals)

    income_groups = ["Low", "Lower-middle", "Middle", "Upper-middle", "High"]
    destinations = ["Public shelter", "Friend/relative home", "Hotel/motel", "Medical facility", "Outside evacuation zone", "Stay in place", "Unknown"]
    dest_values = {}
    spatial = [r for r in rows if r["condition"] == "spatial_grounded"]
    for income in income_groups:
        subset = [r for r in spatial if r["income_level"] == income]
        counts = Counter(r["destination_type"] for r in subset)
        total = len(subset) or 1
        # Plot shelter/hotel/medical/outside as representative stacked-like grouped bars.
        dest_values[(income, "shelter")] = counts["Public shelter"] / total
        dest_values[(income, "hotel")] = counts["Hotel/motel"] / total
    grouped_bar(figure_dir / "destination_by_income.png", "Destination Type By Income", income_groups, ["shelter", "hotel"], dest_values)

    by_persona = defaultdict(dict)
    for r in rows:
        by_persona[(r["persona_id"], r["condition"])].setdefault("scores", []).append(float(r["feasibility_score"]))
    improvements = []
    for pid in sorted({r["persona_id"] for r in rows}):
        base_scores = by_persona[(pid, "baseline")]["scores"]
        spatial_scores = by_persona[(pid, "spatial_grounded")]["scores"]
        if not base_scores or not spatial_scores:
            continue
        base = sum(base_scores) / len(base_scores)
        spatial_score = sum(spatial_scores) / len(spatial_scores)
        improvements.append(spatial_score - base)
    bins = ["<-0.1", "-0.1-0", "0-0.1", "0.1-0.2", ">0.2"]
    counts = [0, 0, 0, 0, 0]
    for v in improvements:
        if v < -0.1:
            counts[0] += 1
        elif v < 0:
            counts[1] += 1
        elif v < 0.1:
            counts[2] += 1
        elif v < 0.2:
            counts[3] += 1
        else:
            counts[4] += 1
    total = len(improvements) or 1
    simple_bar(figure_dir / "feasibility_improvement.png", "Spatial Grounding Improvement", bins, [c / total for c in counts])

    print(f"Wrote figures to {figure_dir}")


if __name__ == "__main__":
    main()
