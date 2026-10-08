"""Build burned-in captions (.ass) from the word timestamps of the kept segments.

Called by assemble.py when the edit plan has "captions": {...}. Style keys (all optional):
  font, size (px at 1080p height), color, highlight (current word), outline_color,
  outline (px), position ("bottom" | "middle" | "top"), max_words (per caption), uppercase
Colours are "#RRGGBB".
"""

import json
from pathlib import Path

from common import ROOT

DEFAULT = {"font": "Montserrat", "size": 64, "color": "#FFFFFF", "highlight": "#FFD60A", "outline_color": "#000000",
           "outline": 4, "position": "bottom", "max_words": 4, "uppercase": False, "bold": True}


def ass_color(hex_rgb: str, alpha: int = 0) -> str:
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def ass_time(t: float) -> str:
    cs = int(round(max(t, 0) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def timeline_words(edl: dict, seg_starts: list[float]) -> list[dict]:
    """Words of every kept segment, moved onto the output timeline."""
    out = []
    for seg, o in zip(edl["segments"], seg_starts):
        if seg.get("captions") is False:
            continue
        tpath = ROOT / "transcripts" / edl["project"] / f"{Path(seg['src']).stem}.json"
        if not tpath.exists():
            continue
        words = json.loads(tpath.read_text())["words"]
        for w in words:
            mid = (w["s"] + w["e"]) / 2
            if seg["in"] <= mid < seg["out"]:
                out.append({"w": w["w"], "s": o + max(w["s"], seg["in"]) - seg["in"],
                            "e": o + min(w["e"], seg["out"]) - seg["in"]})
    return out


def build(edl: dict, seg_starts: list[float], width: int, height: int, dst: Path) -> Path | None:
    style = {**DEFAULT, **(edl.get("captions") or {})}
    words = timeline_words(edl, seg_starts)
    if not words:
        return None
    scale = height / 1080 if width >= height else width / 1080
    size = int(style["size"] * scale)
    align = {"bottom": 2, "middle": 5, "top": 8}[style["position"]]
    margin_v = int((0.12 if style["position"] != "middle" else 0) * height)
    hl = ass_color(style["highlight"])
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{style['font']},{size},{ass_color(style['color'])},{hl},{ass_color(style['outline_color'])},&H80000000,{-1 if style['bold'] else 0},0,0,0,100,100,0,0,1,{style['outline'] * scale:.1f},0,{align},{int(width * 0.08)},{int(width * 0.08)},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Group words into short captions, breaking at pauses and sentence ends.
    groups, cur = [], []
    for w in words:
        if cur and (len(cur) >= style["max_words"] or w["s"] - cur[-1]["e"] > 0.5 or cur[-1]["w"][-1:] in ".?!"):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    lines = []
    for gi, g in enumerate(groups):
        end_of_group = min(g[-1]["e"] + 0.3, groups[gi + 1][0]["s"]) if gi + 1 < len(groups) else g[-1]["e"] + 0.3
        for k, w in enumerate(g):
            s = w["s"]
            e = g[k + 1]["s"] if k + 1 < len(g) else end_of_group
            if e <= s:
                continue
            text = " ".join((("{\\c" + hl + "}" + x["w"] + "{\\r}") if j == k else x["w"]) for j, x in enumerate(g))
            if style["uppercase"]:
                text = text.upper().replace("{\\C", "{\\c").replace("{\\R}", "{\\r}")
            lines.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{text}")
    dst.write_text(header + "\n".join(lines) + "\n")
    return dst
