"""Uji kontras warna dashboard (tema biru gelap) terhadap WCAG 2.2.
  - SC 1.4.3  Contrast (Minimum): teks >= 4.5:1     - SC 1.4.11 Non-text Contrast: elemen grafik >= 3:1
Jalankan:  python tests/test_contrast.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))
import ui  # noqa: E402


def luminance(h):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


CHECKS = [
    ("Teks utama pada panel", ui.TEXT, ui.PANEL, 4.5), ("Teks sekunder pada panel", ui.SUBTEXT, ui.PANEL, 4.5),
    ("Teks sekunder pada latar", ui.SUBTEXT, ui.BG, 4.5), ("Label insight", ui.TEXT_ACCENT, "#EEF0FF", 4.5),
    ("Label rekomendasi", ui.TAG2, "#EEF0FF", 4.5), ("Teks utama pada kotak insight", ui.TEXT, "#EEF0FF", 4.5),
    ("Batang koral (di atas rata-rata)", ui.PRIMARY, ui.PANEL, 3.0), ("Batang/penanda indigo", ui.CYAN, ui.PANEL, 3.0),
    ("Batang biru", ui.BLUE, ui.PANEL, 3.0), ("Garis tren mint", ui.LIME, ui.PANEL, 3.0),
    ("Batang netral/sampel kecil (MUTED)", ui.MUTED, ui.PANEL, 3.0),
]


def test_contrast():
    gagal = [(n, round(ratio(c, bg), 2), m) for n, c, bg, m in CHECKS if ratio(c, bg) < m]
    assert not gagal, f"Kontras di bawah batas: {gagal}"


if __name__ == "__main__":
    bad = 0
    for n, c, bg, m in CHECKS:
        r = ratio(c, bg); bad += r < m
        print(f"{n:42} {c} on {bg}  {r:5.2f} (min {m})  {'LULUS' if r >= m else 'GAGAL'}")
    print(f"\n{len(CHECKS) - bad}/{len(CHECKS)} lulus"); sys.exit(1 if bad else 0)
