"""Generate the Armature Metrics Dashboard as a PNG image."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1200, 1650
BG_TOP = (15, 15, 30)
BG_BOT = (22, 33, 62)

PILLAR_COLORS = {
    "budget":  ((76, 175, 80),  (102, 187, 106)),
    "quality": ((33, 150, 243), (66, 165, 245)),
    "arch":    ((156, 39, 176), (171, 71, 188)),
    "context": ((255, 152, 0),  (255, 183, 77)),
    "gc":      ((244, 67, 54),  (239, 83, 80)),
    "heal":    ((0, 150, 136),  (38, 166, 154)),
}

def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def try_font(size, bold=False):
    names = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    if bold:
        names = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ] + names
    for n in names:
        if os.path.exists(n):
            return ImageFont.truetype(n, size)
    return ImageFont.load_default()


def rounded_rect(draw, xy, radius, fill, outline=None):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def draw_gradient_bg(img):
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        c = lerp_color(BG_TOP, BG_BOT, t)
        draw.line([(0, y), (W, y)], fill=c)


def draw_pillar_card(draw, x, y, w, h, title, subtitle, metrics, color_key):
    c1, c2 = PILLAR_COLORS[color_key]

    # Card background
    rounded_rect(draw, (x, y, x+w, y+h), 14, fill=(30, 30, 50), outline=(50, 50, 70))

    # Icon circle
    icon_size = 38
    ix, iy = x + 18, y + 16
    rounded_rect(draw, (ix, iy, ix+icon_size, iy+icon_size), 10, fill=c1)

    # Pillar icon text
    icons = {"budget": "$", "quality": "Q", "arch": "A", "context": "C", "gc": "GC", "heal": "H"}
    icon_font = try_font(18, bold=True)
    icon_text = icons.get(color_key, "?")
    bb = draw.textbbox((0, 0), icon_text, font=icon_font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((ix + (icon_size - tw) // 2, iy + (icon_size - th) // 2 - 2), icon_text, fill=(255, 255, 255), font=icon_font)

    # Title
    title_font = try_font(15, bold=True)
    draw.text((ix + icon_size + 12, iy + 2), title, fill=(255, 255, 255), font=title_font)

    # Subtitle
    sub_font = try_font(11)
    draw.text((ix + icon_size + 12, iy + 22), subtitle, fill=(160, 160, 180), font=sub_font)

    # Metrics list
    metric_font = try_font(12)
    badge_font = try_font(9, bold=True)
    my = y + 68
    for metric_text in metrics:
        badge = None
        if "|" in metric_text:
            metric_text, badge = metric_text.rsplit("|", 1)
            metric_text = metric_text.strip()
            badge = badge.strip()

        # Dot
        draw.ellipse((x + 20, my + 4, x + 28, my + 12), fill=c1)

        # Text
        draw.text((x + 35, my - 1), metric_text, fill=(210, 210, 220), font=metric_font)

        # Badge
        if badge:
            bb = draw.textbbox((0, 0), badge, font=badge_font)
            bw = bb[2] - bb[0] + 12
            bx = x + w - bw - 14
            badge_bg = (*c1, 40)
            rounded_rect(draw, (bx, my - 1, bx + bw, my + 14), 6, fill=(c1[0]//4, c1[1]//4, c1[2]//4))
            draw.text((bx + 6, my), badge, fill=c2, font=badge_font)

        # Separator line
        if metric_text != metrics[-1]:
            draw.line([(x + 18, my + 20), (x + w - 18, my + 20)], fill=(45, 45, 65), width=1)

        my += 24


def draw_stat_card(draw, x, y, w, h, number, label, color):
    rounded_rect(draw, (x, y, x+w, y+h), 12, fill=(30, 30, 50), outline=(50, 50, 70))
    num_font = try_font(32, bold=True)
    label_font = try_font(10)

    bb = draw.textbbox((0, 0), number, font=num_font)
    tw = bb[2] - bb[0]
    draw.text((x + (w - tw) // 2, y + 14), number, fill=color, font=num_font)

    bb2 = draw.textbbox((0, 0), label, font=label_font)
    tw2 = bb2[2] - bb2[0]
    draw.text((x + (w - tw2) // 2, y + 56), label, fill=(130, 130, 150), font=label_font)


def draw_quality_section(draw, x, y, w):
    # Section background
    rounded_rect(draw, (x, y, x+w, y+230), 14, fill=(20, 30, 55), outline=(33, 80, 140))

    title_font = try_font(16, bold=True)
    draw.text((x + 24, y + 18), "Quality Checks  —  v0.2.1 Implemented + Roadmap", fill=(100, 181, 246), font=title_font)

    categories = [
        ("Implemented", ["Lint scoring (ruff/eslint)", "Type-check (mypy/tsc)", "Test pass/fail + coverage", "Cyclomatic complexity", "Weighted gate scoring"]),
        ("New in v0.2.1", ["Bandit security scan", "Test-to-code LOC ratio", "Docstring coverage (AST)", "Dependency CVE audit", "Baseline regression deltas"]),
        ("Scoring", ["Weighted mean aggregation", "3 gate levels (70/85/95%)", "Per-check weight config", "Tool-missing graceful skip", "Internal check support"]),
        ("Roadmap", ["Cognitive complexity", "Mutation testing", "Flaky test detection", "Change failure rate", "Agent edit accuracy"]),
    ]

    card_w = (w - 80) // 4
    card_h = 170
    card_y = y + 52
    icons_text = ["v1", "v2", "Sc", ">>"]
    icon_colors = [(100, 181, 246), (129, 199, 132), (255, 183, 77), (239, 154, 154)]

    cat_font = try_font(10, bold=True)
    item_font = try_font(11)

    for i, (cat_title, items) in enumerate(categories):
        cx = x + 20 + i * (card_w + 16)
        rounded_rect(draw, (cx, card_y, cx + card_w, card_y + card_h), 10, fill=(35, 35, 58))

        # Icon
        icon_font = try_font(22, bold=True)
        draw.text((cx + card_w // 2 - 12, card_y + 8), icons_text[i], fill=icon_colors[i], font=icon_font)

        # Category title
        bb = draw.textbbox((0, 0), cat_title.upper(), font=cat_font)
        tw = bb[2] - bb[0]
        draw.text((cx + (card_w - tw) // 2, card_y + 38), cat_title.upper(), fill=(160, 160, 180), font=cat_font)

        # Items
        iy = card_y + 58
        for item in items:
            bb = draw.textbbox((0, 0), item, font=item_font)
            tw = bb[2] - bb[0]
            draw.text((cx + (card_w - tw) // 2, iy), item, fill=(190, 190, 210), font=item_font)
            iy += 20


def main():
    img = Image.new("RGB", (W, H))
    draw_gradient_bg(img)
    draw = ImageDraw.Draw(img)

    # Header
    header_font = try_font(30, bold=True)
    sub_font = try_font(14)
    title = "Armature Harness — Metrics Dashboard"
    bb = draw.textbbox((0, 0), title, font=header_font)
    tw = bb[2] - bb[0]
    # Gradient text simulation — draw in bright color
    draw.text(((W - tw) // 2, 30), title, fill=(100, 200, 130), font=header_font)

    subtitle = "50+ metrics across 6 governance pillars for AI coding agents"
    bb2 = draw.textbbox((0, 0), subtitle, font=sub_font)
    tw2 = bb2[2] - bb2[0]
    draw.text(((W - tw2) // 2, 68), subtitle, fill=(140, 140, 160), font=sub_font)

    # Stats bar
    stats = [
        ("6", "GOVERNANCE PILLARS", (76, 175, 80)),
        ("55+", "TRACKED METRICS", (33, 150, 243)),
        ("8", "QUALITY CHECKS", (156, 39, 176)),
        ("4", "AI PROVIDERS", (255, 152, 0)),
        ("10", "MODELS ROUTED", (244, 67, 54)),
    ]
    stat_w = 210
    stat_h = 76
    stat_gap = 16
    total_stats_w = 5 * stat_w + 4 * stat_gap
    stat_x_start = (W - total_stats_w) // 2
    for i, (num, label, color) in enumerate(stats):
        sx = stat_x_start + i * (stat_w + stat_gap)
        draw_stat_card(draw, sx, 100, stat_w, stat_h, num, label, color)

    # Pillars — 3x2 grid
    pillars_data = [
        ("BUDGET", "Token & cost governance", [
            "Per-spec token & cost tracking |JSONL",
            "Phase allocation vs targets",
            "Per-provider cost breakdown",
            "Circuit breaker triggers",
            "Semantic cache hit rate",
            "Model routing decisions",
            "Anomaly detection flags",
            "Auto-calibration profiles |NEW",
        ], "budget"),
        ("QUALITY", "8 weighted checks", [
            "Lint violations & score |W:25",
            "Type-check errors & score |W:25",
            "Test pass/fail & coverage |W:20",
            "Cyclomatic complexity (radon) |W:15",
            "Security scan (bandit) |W:20",
            "Test-to-code ratio |W:10",
            "Docstring coverage (AST) |W:10",
            "Dependency CVE audit |W:15",
        ], "quality"),
        ("ARCHITECTURE", "Boundary enforcement", [
            "Layer boundary violations |ENFORCED",
            "Conformance violations",
            "Import rule enforcement",
            "Base class compliance",
            "Required method checks",
            "Schema-DDL sync",
            "Coupling analysis |PLANNED",
        ], "arch"),
        ("CONTEXT", "Progressive disclosure", [
            "Context window utilization",
            "File read token estimates",
            "Cacheable content %",
            "Narrow scope optimization",
            "Spec token footprint",
            "Conversation token tracking",
        ], "context"),
        ("GARBAGE COLLECTION", "Drift & dead code detection", [
            "Stale doc references |AUTO",
            "Oversized functions",
            "Orphaned test files",
            "Architecture drift",
            "Budget overrun alerts",
            "Dead code detection",
        ], "gc"),
        ("SELF-HEAL", "Auto-fix pipeline", [
            "Lint auto-fix success rate |3-TRY",
            "Type error remaining count",
            "Test failure resolution",
            "Circuit breaker state",
            "Heal attempt history",
            "Failure report generation",
        ], "heal"),
    ]

    card_w = 370
    card_h = 280
    gap = 20
    start_x = (W - (3 * card_w + 2 * gap)) // 2
    start_y = 200

    for i, (title, subtitle, metrics, ckey) in enumerate(pillars_data):
        row, col = divmod(i, 3)
        px = start_x + col * (card_w + gap)
        py = start_y + row * (card_h + gap)
        draw_pillar_card(draw, px, py, card_w, card_h, title, subtitle, metrics, ckey)

    # Quality Deep Dive
    qdv_y = start_y + 2 * (card_h + gap) + 10
    draw_quality_section(draw, start_x, qdv_y, 3 * card_w + 2 * gap)

    # Footer
    footer_y = qdv_y + 250
    draw.line([(start_x, footer_y), (start_x + 3 * card_w + 2 * gap, footer_y)], fill=(50, 50, 70), width=1)

    url_font = try_font(16, bold=True)
    tag_font = try_font(12)

    url_text = "github.com/vivekgana/armature"
    bb = draw.textbbox((0, 0), url_text, font=url_font)
    tw = bb[2] - bb[0]
    draw.text(((W - tw) // 2, footer_y + 14), url_text, fill=(100, 181, 246), font=url_font)

    tag_text = "pip install armature-harness   |   Open Source (MIT)   |   v0.2.1"
    bb2 = draw.textbbox((0, 0), tag_text, font=tag_font)
    tw2 = bb2[2] - bb2[0]
    draw.text(((W - tw2) // 2, footer_y + 40), tag_text, fill=(110, 110, 130), font=tag_font)

    # Save
    out_dir = os.path.dirname(os.path.abspath(__file__))
    png_path = os.path.join(out_dir, "linkedin-metrics-diagram.png")
    jpg_path = os.path.join(out_dir, "linkedin-metrics-diagram.jpg")
    img.save(png_path, "PNG")
    img.save(jpg_path, "JPEG", quality=95)
    print(f"Saved: {png_path}")
    print(f"Saved: {jpg_path}")


if __name__ == "__main__":
    main()
