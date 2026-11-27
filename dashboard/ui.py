"""Tema dan komponen tampilan bersama: tema biru gelap, kartu KPI, kotak insight, format angka Indonesia."""
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Palet terang: indigo = identitas, koral = risiko / di atas rata-rata, mint = baik / tren.
BG, PANEL, TEXT, SUBTEXT = "#F4F5FA", "#FFFFFF", "#111827", "#5B6475"
CYAN, BLUE, LIME, GOOD = "#5B4EF5", "#2F80ED", "#0F9F85", "#0F9F85"   # nama lama dipertahankan agar halaman tidak perlu diubah
TAG2 = "#0B7A66"         # teks label rekomendasi
PRIMARY = "#E5533D"      # koral: pembatalan tinggi / di atas rata-rata
TEXT_ACCENT = "#4F46E5"  # teks label insight
DARK = TEXT              # garis referensi
SLATE, MUTED = "#64748B", "#7D8BB0"
GRID = "rgba(100,116,139,.18)"
ACTOR_COLORS = {"Pembeli": CYAN, "Sistem": BLUE, "Penjual": GOOD}
BACA_RATE = ("Panjang batang = cancel rate, yaitu persen order yang dibatalkan pada kelompok itu. Angka \"... order\" di kanan = jumlah order "
             "kelompok itu; makin sedikit order, makin lemah untuk disimpulkan. Garis putus-putus = rata-rata seluruh order, dan batang koral "
             "berada di atasnya.")
MIN_SAMPLE = 150  # di bawah ini angka persentase ditandai "sampel kecil"


def id_num(x, d=0):
    """Format angka gaya Indonesia: titik ribuan, koma desimal (1.234,5)."""
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d=1):
    return f"{id_num(x, d)}%"


def rp_juta(v):
    return f"Rp{id_num(v / 1e6, 1)} jt"


BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]


def bulan(d, full=False):
    """Nama bulan Indonesia: bulan(ts) -> 'Des 2023'; bulan(ts, True) -> 'Desember 2023'."""
    name = BULAN[d.month - 1]
    return f"{name if full else name[:3]} {d.year}"


def style():
    st.markdown("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
      html, body, [class*="css"], .stMarkdown {font-family: 'Plus Jakarta Sans', sans-serif;}
      .stApp {background: #F4F5FA;}
      .block-container {padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1320px;}
      h1 {font-size: 1.7rem !important; font-weight: 700 !important; margin-bottom: .1rem; color: #111827;}
      [data-testid="stSidebar"] {background: #FFFFFF; border-right: 1px solid #E8EAF3;}
      [data-testid="stSidebarNavLink"] {border-radius: 10px;}
      .kpi {position: relative; min-height: 164px; height: 164px; box-sizing: border-box; background: #FFFFFF; border: 1px solid #E8EAF3; border-radius: 16px;
            padding: 16px 18px 12px; box-shadow: 0 2px 14px rgba(17,24,39,.06);}
      .kpi::before {content: ""; position: absolute; left: 18px; top: 0; width: 36px; height: 4px; border-radius: 0 0 4px 4px; background: var(--accent);}
      .kpi .label {font-size: .84rem; font-weight: 600; color: #111827; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
      .kpi .value {font-size: 1.7rem; font-weight: 700; line-height: 1.4; white-space: nowrap; color: #111827;}
      .kpi .value small {font-size: .95rem; font-weight: 600; color: #5B6475; margin-left: 4px;}
      .kpi.long .value {font-size: 1.1rem; white-space: normal; overflow-wrap: anywhere; line-height: 1.45; padding-top: .2rem;}
      .kpi .sub {font-size: .78rem; color: #5B6475; line-height: 1.35;}
      .kpi .bar {height: 6px; border-radius: 3px; background: #E8EAF3; margin: 2px 0 8px; overflow: hidden;}
      .kpi .bar i {display: block; height: 100%; border-radius: 3px;}
      .kpi .bar.off {visibility: hidden;}
      .ptitle {font-weight: 700; font-size: 1rem; margin: .5rem 0 .35rem; color: #111827;}
      .ptitle::before {content: ""; display: inline-block; width: 8px; height: 8px; margin-right: 8px; border-radius: 50%; background: #5B4EF5;}
      [data-testid="stPlotlyChart"] {background: #FFFFFF; border: 1px solid #E8EAF3; border-radius: 16px; padding: 0; overflow: hidden;
                                     box-shadow: 0 2px 14px rgba(17,24,39,.06);}
      .lg span {margin-right: 16px; font-size: .85rem; color: #5B6475;}
      .lg i {display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px;}
      .insight {background: #EEF0FF; border: 1px solid #DDE0FA; border-left: 4px solid #5B4EF5; border-radius: 16px;
                padding: 6px 20px 14px; margin: 1.3rem 0 .8rem;}
      .insight .row {display: grid; grid-template-columns: 104px 1fr; gap: 10px; margin-top: .65rem; font-size: .93rem; line-height: 1.5; color: #111827;}
      .insight .tag {font-weight: 700; color: #4F46E5;}
      .insight .row:last-child .tag {color: #0B7A66;}
      .insight summary {cursor: pointer; color: #5B6475; font-size: .85rem; margin-top: .6rem;}
      [data-testid="stExpander"] details {background: #FFFFFF; border: 1px solid #E8EAF3; border-radius: 16px;}
      .baca {font-size: .82rem; color: #5B6475; line-height: 1.5; margin: .55rem .2rem .2rem;}
      .note {font-size: .8rem; color: #5B6475; margin-top: .9rem;}
      [data-baseweb="tab-border"] {display: none !important;}
      [data-baseweb="tab-list"] {width: fit-content !important; max-width: 100%;}
      [data-testid="stMain"] [data-testid="stVerticalBlock"] {gap: 1.25rem;}
      [data-testid="stCaptionContainer"] {margin-bottom: .5rem;}
    </style>""", unsafe_allow_html=True)


def kpi(col, label, value, sub="", accent=PRIMARY, unit="", ring=None):
    """Kartu KPI. Jika ring (0-100) diisi, bar tipis di bawah angka menunjukkan persentasenya."""
    p = 0.0 if ring is None else max(0.0, min(float(ring), 100.0))
    bar = f'<div class="bar{"" if ring is not None else " off"}"><i style="width:{p:.1f}%;background:{accent}"></i></div>'
    u = f"<small>{unit}</small>" if unit else ""
    long = " long" if len(str(value)) > 12 else ""   # teks panjang (mis. nama file) boleh turun baris
    col.markdown(f'<div class="kpi{long}" style="--accent:{accent}"><div class="label">{label}</div>'
                 f'<div class="value">{value}{u}</div>{bar}<div class="sub">{sub}</div></div>', unsafe_allow_html=True)


def insight(apa, mengapa, dampak, rekomendasi):
    """Pola wajib dosen: Apa -> Mengapa -> Dampak -> Rekomendasi (semua langsung terlihat)."""
    rows = [("Apa", apa), ("Mengapa", mengapa), ("Dampak", dampak), ("Rekomendasi", rekomendasi)]
    html = "".join(f'<div class="row"><span class="tag">{t}</span><span>{x}</span></div>' for t, x in rows)
    st.markdown(f'<div class="insight">{html}</div>', unsafe_allow_html=True)


def legend(items):
    st.markdown('<div class="lg">' + "".join(f'<span><i style="background:{c}"></i>{n}</span>' for n, c in items.items())
                + "</div>", unsafe_allow_html=True)


def tidy(fig, height=340):
    m = fig.layout.margin
    fig.update_layout(height=height, margin=dict(l=16, t=36, b=34, r=m.r if m.r is not None else 16),
                      font=dict(size=12, color=TEXT, family="Plus Jakarta Sans, sans-serif"), separators=",.",
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(showgrid=False, linecolor=GRID, zerolinecolor=GRID, automargin=True)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)
    return fig


def show(fig, height=None):
    """Judul grafik dipindah ke HTML di atas grafik (tidak lagi bertabrakan dengan legenda); toolbar plotly disembunyikan."""
    t = fig.layout.title.text or ""
    fig.update_layout(title=None)
    if t:
        st.markdown(f'<div class="ptitle">{t}</div>', unsafe_allow_html=True)
    st.plotly_chart(tidy(fig, height or fig.layout.height or 340), width="stretch", config={"displayModeBar": False})
    baca = fig.layout.meta
    if isinstance(baca, str) and baca:
        st.markdown(f'<div class="baca"><b>Cara membaca:</b> {baca}</div>', unsafe_allow_html=True)


def hbar(labels, values, texts, colors, title, height=340, ref=None, ref_label="", xtitle="", baca=None):
    """Batang horizontal dengan kolom nilai di kanan, sehingga label tidak pernah tertimpa garis rata-rata."""
    fig = go.Figure(go.Bar(y=labels, x=values, orientation="h", marker_color=colors, hoverinfo="skip"))
    for lab, tx in zip(labels, texts):
        fig.add_annotation(x=1.0, xref="paper", y=lab, yref="y", text=tx, showarrow=False, xanchor="left", xshift=8,
                           font=dict(size=12, color=SUBTEXT))
    if ref is not None:
        fig.add_vline(x=ref, line_dash="dash", line_color=TEXT, opacity=.7, annotation_text=ref_label, annotation_position="top")
    fig.update_xaxes(range=[0, max(max(values) * 1.08, 5)], title=xtitle)
    fig.update_layout(title=title, height=height, margin=dict(r=170), meta=baca)
    return fig


def idf(df, dec=None):
    """Salinan tabel dengan angka berformat Indonesia (titik ribuan, koma desimal) untuk st.dataframe."""
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_numeric_dtype(out[c]) and not pd.api.types.is_bool_dtype(out[c]):
            d = (dec or {}).get(c, 0)
            out[c] = out[c].map(lambda v, d=d: id_num(v, d))
    return out


def id_text(t):
    """Ubah teks angka berformat Inggris (20,848 / 1,234.50) menjadi format Indonesia; teks lain dibiarkan."""
    x = str(t)
    return x.replace(",", "X").replace(".", ",").replace("X", ".") if re.fullmatch(r"-?[\d,]+(\.\d+)?", x) else x
