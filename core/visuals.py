from __future__ import annotations

from io import BytesIO
from typing import Iterable


def _try_import_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
        return Image, ImageDraw, ImageFont
    except Exception:
        return None, None, None


def _font(ImageFont, size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _wrap_text(draw, text: str, font, max_width: int) -> list[str]:
    words = str(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    try:
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    except Exception:
        draw.rectangle(xy, fill=fill, outline=outline, width=width)


def make_schedule_card(title: str, subtitle: str, items: Iterable[dict], footer: str = "XML Helper") -> BytesIO | None:
    """Create a clean PNG timetable card. Returns None if Pillow is unavailable."""
    Image, ImageDraw, ImageFont = _try_import_pillow()
    if not Image:
        return None

    items = list(items)
    width = 1200
    header_h = 210
    row_base = 132
    height = header_h + max(1, len(items)) * row_base + 110
    img = Image.new("RGB", (width, height), "#0b1020")
    draw = ImageDraw.Draw(img)

    # Gradient background
    for y in range(height):
        r = int(11 + (35 - 11) * y / height)
        g = int(16 + (46 - 16) * y / height)
        b = int(32 + (86 - 32) * y / height)
        draw.line((0, y, width, y), fill=(r, g, b))

    title_font = _font(ImageFont, 58, True)
    subtitle_font = _font(ImageFont, 30, False)
    row_time_font = _font(ImageFont, 34, True)
    row_title_font = _font(ImageFont, 34, True)
    row_meta_font = _font(ImageFont, 25, False)
    footer_font = _font(ImageFont, 22, False)

    draw.text((60, 48), title, font=title_font, fill="#ffffff")
    draw.text((64, 122), subtitle, font=subtitle_font, fill="#b8c7ff")

    y = header_h
    if not items:
        _rounded_rect(draw, (55, y, width - 55, y + 120), 28, "#ffffff")
        draw.text((95, y + 38), "No items scheduled 🎉", font=row_title_font, fill="#172033")
    else:
        for idx, item in enumerate(items):
            row_h = row_base
            x1, y1, x2, y2 = 55, y, width - 55, y + row_h - 18
            _rounded_rect(draw, (x1, y1, x2, y2), 28, "#ffffff")
            accent = ["#4f46e5", "#06b6d4", "#22c55e", "#f97316", "#ec4899"][idx % 5]
            _rounded_rect(draw, (x1, y1, x1 + 18, y2), 12, accent)

            time_text = item.get("time", "")
            subject = item.get("title", "Untitled")
            meta = item.get("meta", "")
            draw.text((95, y1 + 28), time_text, font=row_time_font, fill=accent)
            lines = _wrap_text(draw, subject, row_title_font, 650)
            draw.text((355, y1 + 23), lines[0], font=row_title_font, fill="#111827")
            if len(lines) > 1:
                draw.text((355, y1 + 62), lines[1], font=row_meta_font, fill="#374151")
            draw.text((355, y1 + 82), meta, font=row_meta_font, fill="#6b7280")
            y += row_h

    draw.text((60, height - 52), footer, font=footer_font, fill="#cbd5e1")
    out = BytesIO()
    img.save(out, format="PNG", optimize=True)
    out.seek(0)
    out.name = "xml_helper_card.png"
    return out


def make_train_card(title: str, train: dict | None, footer: str = "XML Helper") -> BytesIO | None:
    Image, ImageDraw, ImageFont = _try_import_pillow()
    if not Image:
        return None

    width, height = 1200, 680
    img = Image.new("RGB", (width, height), "#08111f")
    draw = ImageDraw.Draw(img)
    for y in range(height):
        r = int(8 + (20 - 8) * y / height)
        g = int(17 + (68 - 17) * y / height)
        b = int(31 + (105 - 31) * y / height)
        draw.line((0, y, width, y), fill=(r, g, b))

    title_font = _font(ImageFont, 58, True)
    big_font = _font(ImageFont, 74, True)
    label_font = _font(ImageFont, 28, False)
    normal_font = _font(ImageFont, 36, True)
    small_font = _font(ImageFont, 24, False)

    draw.text((60, 48), title, font=title_font, fill="#ffffff")
    _rounded_rect(draw, (60, 160, width - 60, 560), 36, "#ffffff")

    if not train:
        draw.text((115, 310), "No more trains available today 🌙", font=normal_font, fill="#111827")
    else:
        train_no = str(train.get("train_number", "N/A"))
        dep = train.get("departure_time", train.get("departure", "N/A"))
        arr = train.get("arrival_time", train.get("arrival", "N/A"))
        route = train.get("route_name", "")
        time_to = train.get("time_to_text", "")
        warning = "Does not run Sundays/holidays" if not train.get("operates_weekends", True) else "Runs normally"

        draw.text((115, 205), f"Train {train_no}", font=big_font, fill="#111827")
        draw.text((115, 306), route, font=label_font, fill="#64748b")

        draw.text((115, 390), "Departure", font=label_font, fill="#64748b")
        draw.text((115, 428), dep, font=normal_font, fill="#2563eb")
        draw.text((450, 390), "Arrival", font=label_font, fill="#64748b")
        draw.text((450, 428), arr, font=normal_font, fill="#16a34a")
        draw.text((760, 390), "Leaves", font=label_font, fill="#64748b")
        draw.text((760, 428), time_to or "soon", font=normal_font, fill="#ea580c")
        draw.text((115, 505), warning, font=small_font, fill="#991b1b" if "Does" in warning else "#166534")

    draw.text((60, height - 52), footer, font=small_font, fill="#cbd5e1")
    out = BytesIO()
    img.save(out, format="PNG", optimize=True)
    out.seek(0)
    out.name = "xml_helper_train.png"
    return out
