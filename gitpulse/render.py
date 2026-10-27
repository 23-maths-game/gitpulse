"""Self-contained HTML renderer.

The output is a **single file** with inline CSS and inline SVG: no fonts, no CDN,
no JavaScript. It renders identically offline, in a sandboxed iframe, in an
e-mail attachment, or committed straight into a repo as a CI artifact.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

from .metrics import Delta, extension_breakdown
from .models import Analysis

ACCENT = "#38bdf8"
ACCENT_2 = "#a78bfa"
WARN = "#f59e0b"

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

CSS = """
:root{
  --bg:#080b10; --panel:#0f151d; --panel-2:#131c26; --line:#1e2a36;
  --text:#e6edf3; --muted:#8b9bab; --accent:#38bdf8; --accent-2:#a78bfa;
  --ok:#34d399; --warn:#f59e0b; --del:#f87171;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  background:
    radial-gradient(1100px 500px at 12% -12%, rgba(56,189,248,.13), transparent 60%),
    radial-gradient(900px 460px at 92% -6%, rgba(167,139,250,.12), transparent 60%),
    var(--bg);
  color:var(--text);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased;
  padding:40px 22px 64px;
}
.wrap{max-width:1060px;margin:0 auto}
header.top{display:flex;flex-wrap:wrap;gap:18px;align-items:flex-end;justify-content:space-between;margin-bottom:26px}
.brand{display:flex;align-items:center;gap:13px}
.pulse{width:38px;height:38px;border-radius:11px;background:linear-gradient(140deg,var(--accent),var(--accent-2));
  display:grid;place-items:center;box-shadow:0 0 0 1px rgba(255,255,255,.08),0 10px 26px -10px var(--accent)}
h1{font-size:27px;margin:0;letter-spacing:-.4px;font-weight:700}
.sub{color:var(--muted);font-size:13px;margin-top:3px}
.pill{display:inline-flex;align-items:center;gap:7px;background:var(--panel);border:1px solid var(--line);
  color:var(--muted);font-size:12px;padding:5px 11px;border-radius:999px;margin-left:6px;white-space:nowrap}
.dot{width:6px;height:6px;border-radius:50%;background:var(--ok);box-shadow:0 0 8px var(--ok)}
.grid{display:grid;gap:15px}
.kpis{grid-template-columns:repeat(auto-fit,minmax(152px,1fr));margin-bottom:15px}
.card{background:linear-gradient(180deg,var(--panel),var(--panel-2));border:1px solid var(--line);
  border-radius:14px;padding:16px 17px}
.kpi .label{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.8px;font-weight:600}
.kpi .value{font-size:25px;font-weight:700;letter-spacing:-.6px;margin-top:6px;font-variant-numeric:tabular-nums}
.kpi .hint{color:var(--muted);font-size:11.5px;margin-top:2px}
.kpi.hero .value{background:linear-gradient(120deg,var(--accent),var(--accent-2));
  -webkit-background-clip:text;background-clip:text;color:transparent}
.two{grid-template-columns:1fr 1fr}
@media(max-width:820px){.two{grid-template-columns:1fr}}
h2{font-size:13px;text-transform:uppercase;letter-spacing:1.1px;color:var(--muted);margin:0 0 14px;font-weight:700}
.chart{width:100%;height:auto;display:block;overflow:visible}
.legend{display:flex;gap:16px;flex-wrap:wrap;color:var(--muted);font-size:11.5px;margin-top:10px}
.swatch{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:6px;vertical-align:middle}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:var(--muted);font-weight:600;font-size:11px;text-transform:uppercase;
  letter-spacing:.7px;padding:0 8px 9px;border-bottom:1px solid var(--line)}
td{padding:8px;border-bottom:1px solid rgba(30,42,54,.55);vertical-align:middle}
tr:last-child td{border-bottom:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px}
.path{color:#cfe3f3;word-break:break-all}
.add{color:var(--ok)}.del{color:var(--del)}
.bar{height:6px;border-radius:99px;background:rgba(255,255,255,.06);overflow:hidden;min-width:60px}
.bar > i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--accent),var(--accent-2))}
.author{display:flex;align-items:center;gap:11px;padding:8px 0;border-bottom:1px solid rgba(30,42,54,.55)}
.author:last-child{border-bottom:0}
.avatar{width:29px;height:29px;border-radius:9px;display:grid;place-items:center;font-size:12px;font-weight:700;
  color:#04121c;background:linear-gradient(140deg,var(--accent),var(--accent-2));flex:none}
.who{flex:1;min-width:0}
.who .n{font-size:13.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.who .m{color:var(--muted);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.count{font-variant-numeric:tabular-nums;font-size:13px;color:var(--muted);flex:none}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:var(--panel-2);border:1px solid var(--line);border-radius:9px;padding:6px 10px;font-size:12px;color:#cbd8e4}
.chip b{color:var(--accent);font-variant-numeric:tabular-nums;margin-left:6px}
.empty{color:var(--muted);font-size:13px;padding:10px 0}
table.cmp td{font-size:13.5px}
table.cmp td.lbl{color:#cbd8e4}
.better{color:var(--ok);font-weight:600}
.worse{color:var(--del);font-weight:600}
.flat{color:var(--muted)}
.pill-note{display:inline-flex;gap:7px;align-items:center;background:rgba(245,158,11,.09);
  border:1px solid rgba(245,158,11,.35);color:#fbbf24;font-size:11.5px;padding:5px 11px;
  border-radius:999px;margin-left:6px}
.headline{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline;margin-bottom:12px}
.headline .big{font-size:19px;font-weight:700;letter-spacing:-.3px}
.headline .vs{color:var(--muted);font-size:12.5px}
footer{margin-top:26px;color:#5f6f7f;font-size:11.5px;text-align:center}
footer a{color:#7c8fa1}
"""


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _n(value: float) -> str:
    """Thousands-separated integer formatting that stays JSON-friendly."""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _pct(part: int, whole: int) -> float:
    return (part / whole * 100.0) if whole else 0.0


def _short_date(iso: str | None) -> str:
    if not iso:
        return "—"
    return datetime.fromisoformat(iso).strftime("%d %b %Y")


# --------------------------------------------------------------------------- #
# SVG builders
# --------------------------------------------------------------------------- #
def _weekly_svg(weekly: list[tuple[str, int]]) -> str:
    """Monday-anchored bar chart of commits per week."""
    if not weekly:
        return '<p class="empty">No activity in range.</p>'

    width, height = 800, 210
    left, right, top, bottom = 34, 8, 14, 30
    plot_w = width - left - right
    plot_h = height - top - bottom
    peak = max((c for _, c in weekly), default=0) or 1
    step = plot_w / len(weekly)
    bar_w = max(2.0, min(30.0, step * 0.62))

    bars, ticks = [], []
    for i, (week, count) in enumerate(weekly):
        h = (count / peak) * plot_h
        x = left + i * step + (step - bar_w) / 2
        y = top + plot_h - h
        bars.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{max(h, 1.2):.2f}" rx="3" '
            f'fill="url(#gp-grad)"><title>{_esc(week)} · {count} commit{"s" if count != 1 else ""}</title></rect>'
        )
        ticks.append((left + i * step + step / 2, week))

    # Gridlines + y labels at 0 / half / peak.
    grid = []
    for frac in (0.0, 0.5, 1.0):
        y = top + plot_h - frac * plot_h
        grid.append(f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" stroke="#1b2733" stroke-width="1"/>')
        grid.append(
            f'<text x="{left - 8}" y="{y + 4:.2f}" fill="#5f6f7f" font-size="10" text-anchor="end">'
            f'{round(frac * peak)}</text>'
        )

    # Label roughly 7 evenly spaced weeks so labels never collide.
    stride = max(1, len(weekly) // 7)
    x_labels = []
    for i, (cx, week) in enumerate(ticks):
        if i % stride and i != len(ticks) - 1:
            continue
        x_labels.append(
            f'<text x="{cx:.2f}" y="{height - 9}" fill="#5f6f7f" font-size="10" text-anchor="middle">'
            f'{_short_date(week)[:6]}</text>'
        )

    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="Commits per week">'
        "<defs>"
        f'<linearGradient id="gp-grad" x1="0" y1="1" x2="0" y2="0">'
        f'<stop offset="0%" stop-color="{ACCENT_2}" stop-opacity=".55"/>'
        f'<stop offset="100%" stop-color="{ACCENT}" stop-opacity=".98"/>'
        "</linearGradient></defs>"
        + "".join(grid)
        + "".join(bars)
        + "".join(x_labels)
        + "</svg>"
    )


def _heatmap_svg(weekday_hour: list[list[int]]) -> str:
    """7×24 punch-card of commit timestamps (author-local hours)."""
    cell, gap = 26, 3.4
    label_w, top = 40, 20
    width = label_w + 24 * (cell + gap) + 6
    height = top + 7 * (cell + gap) + 6
    peak = max((max(row) for row in weekday_hour), default=0)

    parts = []
    for hour in range(0, 24, 3):
        cx = label_w + hour * (cell + gap)
        parts.append(
            f'<text x="{cx:.1f}" y="12" fill="#5f6f7f" font-size="10" text-anchor="start">{hour:02d}h</text>'
        )
    for row, name in enumerate(WEEKDAYS):
        cy = top + row * (cell + gap)
        parts.append(
            f'<text x="{label_w - 9}" y="{cy + cell * 0.68:.1f}" fill="#5f6f7f" font-size="10" text-anchor="end">{name}</text>'
        )
        for hour in range(24):
            count = weekday_hour[row][hour]
            cx = label_w + hour * (cell + gap)
            if count == 0:
                fill, opacity = "#141d27", 1.0
            else:
                # Square-root scale keeps small values visible next to spikes.
                ratio = (count / peak) ** 0.5 if peak else 0
                opacity = 0.28 + 0.72 * ratio
                fill = ACCENT
            parts.append(
                f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell}" height="{cell}" rx="4" fill="{fill}" '
                f'opacity="{opacity:.2f}"><title>{name} {hour:02d}:00 — {count} commit{"s" if count != 1 else ""}</title></rect>'
            )
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="Commits by weekday and hour">'
        + "".join(parts)
        + "</svg>"
    )


# --------------------------------------------------------------------------- #
# HTML fragments
# --------------------------------------------------------------------------- #
def _kpis(a: Analysis) -> str:
    items = [
        ("Commits analysed", _n(a.commits_analyzed), f"of {_n(a.total_commits_in_repo)} in repo", True),
        ("Contributors", _n(len(a.authors)), f"bus factor {a.bus_factor}", False),
        ("Lines added", f'+{_n(a.added)}', f"{_pct(a.added, a.added + a.deleted):.0f}% of churn", False),
        ("Lines deleted", f'-{_n(a.deleted)}', f"net {a.added - a.deleted:+,}", False),
        ("Active days", _n(a.active_days), f"{a.avg_commits_per_active_day:.2f} commits/day", False),
        ("Longest streak", f"{a.longest_streak}d", "consecutive days", False),
    ]
    cards = "".join(
        f'<div class="card kpi{" hero" if hero else ""}">'
        f'<div class="label">{label}</div><div class="value">{value}</div>'
        f'<div class="hint">{_esc(hint)}</div></div>'
        for label, value, hint, hero in items
    )
    return f'<div class="grid kpis">{cards}</div>'


def _authors_panel(a: Analysis) -> str:
    if not a.authors:
        return '<p class="empty">No contributors.</p>'
    top = a.authors[:8]
    peak = max(x.commits for x in top) or 1
    rows = []
    for author in top:
        initials = "".join(p[0] for p in author.name.replace(".", " ").split()[:2]).upper() or "?"
        rows.append(
            '<div class="author">'
            f'<div class="avatar">{_esc(initials)}</div>'
            '<div class="who">'
            f'<div class="n">{_esc(author.name)}</div>'
            f'<div class="m">{_esc(author.email or "no e-mail")}</div>'
            f'<div class="bar" style="margin-top:6px"><i style="width:{author.commits / peak * 100:.1f}%"></i></div>'
            "</div>"
            f'<div class="count">{_n(author.commits)}</div>'
            "</div>"
        )
    return "".join(rows)


def _files_table(a: Analysis) -> str:
    if not a.files:
        return '<p class="empty">No file changes recorded.</p>'
    peak = max(f.changes for f in a.files) or 1
    rows = []
    for rank, f in enumerate(a.files[:12], start=1):
        rows.append(
            "<tr>"
            f'<td class="num" style="color:#5f6f7f">{rank}</td>'
            f'<td class="path mono">{_esc(f.path)}</td>'
            f'<td style="width:130px"><div class="bar"><i style="width:{f.changes / peak * 100:.1f}%"></i></div></td>'
            f'<td class="num">{_n(f.changes)}</td>'
            f'<td class="num add">+{_n(f.added)}</td>'
            f'<td class="num del">-{_n(f.deleted)}</td>'
            "</tr>"
        )
    return (
        "<table><thead><tr><th class=\"num\">#</th><th>File</th><th>Hotness</th>"
        "<th class=\"num\">Touches</th><th class=\"num\">Added</th><th class=\"num\">Deleted</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _types_panel(a: Analysis) -> str:
    chips = []
    for ctype, count in a.commit_types[:10]:
        chips.append(f'<span class="chip">{_esc(ctype)}<b>{_n(count)}</b></span>')
    for ext, count in extension_breakdown(a.files)[:6]:
        chips.append(f'<span class="chip mono">{_esc(ext)}<b>{_n(count)}</b></span>')
    if not chips:
        return '<p class="empty">No Conventional Commit prefixes detected.</p>'
    return f'<div class="chips">{"".join(chips)}</div>'


def _fmt(value: float) -> str:
    """Pretty-print a metric: thousands separators for ints, one decimal otherwise."""
    if isinstance(value, float) and not float(value).is_integer():
        return f"{value:,.2f}"
    return _n(round(value))


def _comparison_panel(deltas: list[Delta], baseline: Analysis) -> str:
    """Period-over-period table: baseline | current | delta, colour-coded."""
    rows = []
    for d in deltas:
        sentiment = d.sentiment
        arrow = "→" if d.change == 0 else ("↑" if d.change > 0 else "↓")
        magnitude = f"{arrow} {_n(abs(round(d.change)))}{d.unit}"
        pct = d.pct
        suffix = f" ({pct:+.0f}%)" if pct is not None else ""
        rows.append(
            "<tr>"
            f'<td class="lbl">{_esc(d.label)}</td>'
            f'<td class="num mono">{_fmt(d.baseline)}{d.unit}</td>'
            f'<td class="num mono">{_fmt(d.current)}{d.unit}</td>'
            f'<td class="num mono {sentiment}">{magnitude}{suffix}</td>'
            "</tr>"
        )

    span = "previous period"
    if baseline.first_commit and baseline.last_commit:
        span = f"{baseline.first_commit:%d %b %Y} → {baseline.last_commit:%d %b %Y}"

    return (
        '<div class="headline">'
        '<span class="big">Current window</span>'
        f'<span class="vs">measured against {_esc(span)}</span>'
        "</div>"
        '<table class="cmp"><thead><tr><th>Metric</th><th class="num">Baseline</th>'
        '<th class="num">Current</th><th class="num">Change</th></tr></thead>'
        "<tbody>" + "".join(rows) + "</tbody></table>"
        '<div class="legend"><span><b class="better">green</b> = improved</span>'
        '<span><b class="worse">red</b> = regressed</span>'
        "<span>grey = neutral metric</span></div>"
    )


def render_html(
    a: Analysis,
    *,
    title: str | None = None,
    comparison: list[Delta] | None = None,
    baseline: Analysis | None = None,
    notes: list[str] | None = None,
) -> str:
    """Render the full report as one self-contained HTML document."""
    page_title = title or f"gitpulse · {a.repo_name}"
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    span = "—"
    if a.first_commit and a.last_commit:
        span = f"{a.first_commit:%d %b %Y} → {a.last_commit:%d %b %Y}"

    streak_note = ""
    if a.streak_start and a.streak_end and a.longest_streak > 1:
        streak_note = f'<div class="hint">best run {a.streak_start:%d %b} → {a.streak_end:%d %b}</div>'

    comparison_card = ""
    if comparison and baseline is not None:
        comparison_card = f'<div class="card" style="margin-bottom:15px"><h2>Period comparison</h2>{_comparison_panel(comparison, baseline)}</div>'

    notes_html = "".join(f'<span class="pill-note">{_esc(n)}</span>' for n in (notes or []))

    body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="generator" content="gitpulse">
<title>{_esc(page_title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div class="brand">
      <div class="pulse" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#04121c" stroke-width="2.4"
             stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h4l3-8 4 16 3-8h6"/></svg>
      </div>
      <div>
        <h1>{_esc(a.repo_name)}</h1>
        <div class="sub">Repository pulse · {_esc(span)}</div>
      </div>
    </div>
    <div>
      <span class="pill"><span class="dot"></span>{_esc(a.branch)}</span>
      <span class="pill mono">{_esc(a.head_sha or "no HEAD")}</span>{notes_html}
    </div>
  </header>

  {_kpis(a)}

  {comparison_card}

  <div class="grid two" style="margin-bottom:15px">
    <div class="card">
      <h2>Commits per week</h2>
      {_weekly_svg(a.weekly)}
      <div class="legend"><span><i class="swatch" style="background:{ACCENT}"></i>commits</span>
      <span>Monday-anchored ISO weeks</span></div>
    </div>
    <div class="card">
      <h2>Punch card</h2>
      {_heatmap_svg(a.weekday_hour)}
      <div class="legend"><span>author-local timezone</span>{streak_note}</div>
    </div>
  </div>

  <div class="grid two" style="margin-bottom:15px">
    <div class="card">
      <h2>Contributors</h2>
      {_authors_panel(a)}
    </div>
    <div class="card">
      <h2>Hotspots &amp; churn</h2>
      {_files_table(a)}
    </div>
  </div>

  <div class="card">
    <h2>Commit prefixes &amp; file types</h2>
    {_types_panel(a)}
  </div>

  <footer>Generated by <b>gitpulse</b> · {generated} · zero dependencies, zero network calls</footer>
</div>
</body>
</html>
"""
    return body
