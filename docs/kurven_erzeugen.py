# -*- coding: utf-8 -*-
"""Erzeugt je Kennlinie eine SVG-Grafik fuer das Warmondo-Dashboard.

Stuetzpunkte von der Anzeige der Regelung abgelesen. Heiz- und Kuehlkurven
haben **verschiedene Achsen**: Heizen zeigt 20 bis -20 Grad Umgebung,
Kuehlen 30 bis -10.
"""
import io, os

# Heizen: Vorlauf-Soll bei 20 / 10 / 0 / -10 / -20 Grad
HEIZKURVEN = {
    "low_temp_1": ("Niedrige Temperatur 1", [32, 33, 35, 37, 38]),
    "low_temp_2": ("Niedrige Temperatur 2", [31, 32, 34, 36, 37]),
    "low_temp_3": ("Niedrige Temperatur 3", [29, 31, 33, 34, 36]),
    "low_temp_4": ("Niedrige Temperatur 4", [28, 30, 32, 33, 35]),
    "low_temp_5": ("Niedrige Temperatur 5", [27, 29, 31, 32, 34]),
    "low_temp_6": ("Niedrige Temperatur 6", [26, 28, 29, 31, 32]),
    "low_temp_7": ("Niedrige Temperatur 7", [25, 27, 28, 30, 31]),
    "low_temp_8": ("Niedrige Temperatur 8", [24, 25, 26, 28, 29]),
    "high_temp_1": ("Hohe Temperatur 1", [50, 51, 53, 54, 55]),
    "high_temp_2": ("Hohe Temperatur 2", [48, 49, 51, 52, 53]),
    "high_temp_3": ("Hohe Temperatur 3", [47, 48, 50, 51, 52]),
    "high_temp_4": ("Hohe Temperatur 4", [45, 46, 48, 49, 50]),
    "high_temp_5": ("Hohe Temperatur 5", [43, 44, 46, 47, 48]),
    "high_temp_6": ("Hohe Temperatur 6", [40, 41, 43, 44, 45]),
    "high_temp_7": ("Hohe Temperatur 7", [38, 39, 41, 42, 43]),
    "high_temp_8": ("Hohe Temperatur 8", [35, 36, 38, 39, 40]),
}
# Kuehlen: Vorlauf-Soll bei 30 / 20 / 10 / 0 / -10 Grad
KUEHLKURVEN = {
    "low_temp_1": ("Niedrige Temperatur 1", [5, 11, 16, 16, 16]),
    "low_temp_2": ("Niedrige Temperatur 2", [6, 12, 17, 17, 17]),
    "low_temp_3": ("Niedrige Temperatur 3", [7, 13, 18, 18, 18]),
    "low_temp_4": ("Niedrige Temperatur 4", [8, 14, 19, 19, 19]),
    "low_temp_5": ("Niedrige Temperatur 5", [9, 15, 20, 20, 20]),
    "low_temp_6": ("Niedrige Temperatur 6", [10, 16, 21, 21, 21]),
    "low_temp_7": ("Niedrige Temperatur 7", [11, 17, 22, 22, 22]),
    "low_temp_8": ("Niedrige Temperatur 8", [12, 18, 23, 23, 23]),
    "high_temp_1": ("Hohe Temperatur 1", [16, 18, 20, 20, 20]),
    "high_temp_2": ("Hohe Temperatur 2", [17, 19, 21, 21, 21]),
    "high_temp_3": ("Hohe Temperatur 3", [17, 20, 22, 22, 22]),
    "high_temp_4": ("Hohe Temperatur 4", [18, 21, 23, 23, 23]),
    "high_temp_5": ("Hohe Temperatur 5", [18, 21, 24, 24, 24]),
    "high_temp_6": ("Hohe Temperatur 6", [19, 22, 24, 24, 24]),
    "high_temp_7": ("Hohe Temperatur 7", [19, 22, 25, 25, 25]),
    "high_temp_8": ("Hohe Temperatur 8", [20, 23, 25, 25, 25]),
}
ACHSE_HEIZEN = [20, 10, 0, -10, -20]
ACHSE_KUEHLEN = [30, 20, 10, 0, -10]
B, H = 520, 300
L, R, O, U = 58, 24, 40, 46
AKZENT_HEIZEN, AKZENT_KUEHLEN = "#f2808e", "#58a6d8"
NL = "\n"


def kopf(titel):
    return (f'<text x="{B-R}" y="26" font-size="16" font-weight="600" fill="#aaa" '
            f'text-anchor="end">{titel}</text>')


def hochachse():
    m = (O + (H - U)) / 2
    return (f'<text x="16" y="{m:.1f}" font-size="12" fill="#888" text-anchor="middle" '
            f'transform="rotate(-90 16 {m:.1f})">Vorlauf-Soll (°C)</text>')


def kurve(titel, werte, achse, ymax, yticks, akzent):
    px = lambda t: L + (achse[0] - t) / (achse[0] - achse[-1]) * (B - L - R)
    py = lambda v: H - U - (v / ymax) * (H - O - U)
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {B} {H}" width="{B}" '
         f'height="{H}" font-family="system-ui,sans-serif"><title>{titel}</title>']
    for v in yticks:
        y = py(v)
        p.append(f'<line x1="{L}" y1="{y:.1f}" x2="{B-R}" y2="{y:.1f}" stroke="#888" stroke-opacity=".25"/>')
        p.append(f'<text x="{L-10}" y="{y+4:.1f}" font-size="13" fill="#888" text-anchor="end">{v}</text>')
    for t in achse:
        x = px(t)
        p.append(f'<line x1="{x:.1f}" y1="{O}" x2="{x:.1f}" y2="{H-U}" stroke="#888" '
                 f'stroke-opacity=".18" stroke-dasharray="3 4"/>')
        p.append(f'<text x="{x:.1f}" y="{H-U+20}" font-size="13" fill="#888" text-anchor="middle">{t}</text>')
    pts = " ".join(f"{px(t):.1f},{py(v):.1f}" for t, v in zip(achse, werte))
    p.append(f'<polyline points="{pts}" fill="none" stroke="{akzent}" stroke-width="3" '
             f'stroke-linejoin="round" stroke-linecap="round"/>')
    for t, v in zip(achse, werte):
        p.append(f'<circle cx="{px(t):.1f}" cy="{py(v):.1f}" r="4.5" fill="{akzent}"/>')
        p.append(f'<text x="{px(t):.1f}" y="{py(v)-12:.1f}" font-size="14" font-weight="600" '
                 f'fill="{akzent}" text-anchor="middle">{v}</text>')
    p.append(kopf(titel))
    p.append(hochachse())
    p.append(f'<text x="{B-R}" y="{H-8}" font-size="12" fill="#888" text-anchor="end">Außentemperatur (°C)</text>')
    p.append('</svg>')
    return NL.join(p)


def aus(text, zusatz):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {B} {H}" width="{B}" '
            f'height="{H}" font-family="system-ui,sans-serif">'
            f'<text x="{B//2}" y="{H//2-6}" font-size="18" fill="#888" text-anchor="middle">{text}</text>'
            f'<text x="{B//2}" y="{H//2+20}" font-size="14" fill="#888" text-anchor="middle">{zusatz}</text></svg>')


def schreibe(pfad, inhalt):
    io.open(pfad, "w", encoding="utf-8", newline=NL).write(inhalt)


for ordner in ("kurven/heizen", "kurven/kuehlen"):
    os.makedirs(ordner, exist_ok=True)
for k, (titel, werte) in HEIZKURVEN.items():
    ymax = 45 if k.startswith("low") else 60
    ticks = [0, 15, 30, 45] if ymax == 45 else [0, 20, 40, 60]
    schreibe(f"kurven/heizen/{k}.svg", kurve(titel, werte, ACHSE_HEIZEN, ymax, ticks, AKZENT_HEIZEN))
for k, (titel, werte) in KUEHLKURVEN.items():
    schreibe(f"kurven/kuehlen/{k}.svg",
             kurve(titel, werte, ACHSE_KUEHLEN, 30, [0, 10, 20, 30], AKZENT_KUEHLEN))
schreibe("kurven/heizen/disabled.svg",
         aus("Heizkennlinie deaktiviert", "Die Vorlauftemperatur wird von Hand vorgegeben."))
schreibe("kurven/kuehlen/disabled.svg",
         aus("Kühlkennlinie deaktiviert", "Die Vorlauftemperatur wird von Hand vorgegeben."))
print("heizen:", len(os.listdir("kurven/heizen")), " kuehlen:", len(os.listdir("kurven/kuehlen")))
