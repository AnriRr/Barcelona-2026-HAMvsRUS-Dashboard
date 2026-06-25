"""
2026 Spanish Grand Prix (Barcelona) — FastF1 Dashboard
"""

import fastf1
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

cache_dir = Path("./f1_cache")
cache_dir.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(str(cache_dir))

print("Loading 2026 Barcelona Grand Prix...")
session = fastf1.get_session(2026, "Barcelona Grand Prix", "R")
session.load(laps=True, telemetry=False, weather=False, messages=False)

DRIVERS = {
    "HAM": {"label": "Hamilton (Ferrari)",  "color": "#E8002D"},
    "RUS": {"label": "Russell (Mercedes)", "color": "#27F4D2"},
}
TIRE_COLORS = {"SOFT": "#FF3333", "MEDIUM": "#FFD700", "HARD": "#CCCCCC"}
BG, PANEL, GRID, TEXT = "#0D0D0D", "#161616", "#2a2a2a", "#C8C8C8"
YELLOW, ORANGE = "#FFE045", "#FF8C00"

# VSC/SC bands
ref_laps = session.laps.pick_drivers("HAM").copy()
ref_laps["IsVSC"] = ref_laps["TrackStatus"].astype(str).str.contains("6")
ref_laps["IsSC"]  = ref_laps["TrackStatus"].astype(str).str.contains("4")

def get_status_bands(df, col, label):
    status_laps = df[df[col]]["LapNumber"].values
    if len(status_laps) == 0:
        return []
    bands = []
    start = status_laps[0]
    prev  = status_laps[0]
    for lap in status_laps[1:]:
        if lap > prev + 1:
            bands.append((start, prev, label))
            start = lap
        prev = lap
    bands.append((start, prev, label))
    return bands

all_bands = get_status_bands(ref_laps, "IsVSC", "VSC") + get_status_bands(ref_laps, "IsSC", "SC")

print("\nTrack status periods detected:")
for start, end, kind in sorted(all_bands, key=lambda x: x[0]):
    print(f"  {kind}: Lap {int(start)} – {int(end)}")

# Process laps
laps = {}
for drv in DRIVERS:
    df = session.laps.pick_drivers(drv).copy().reset_index(drop=True)
    df["LapTimeSec"] = df["LapTime"].dt.total_seconds()
    df["IsPitLap"]   = df["PitInTime"].notna() | df["PitOutTime"].notna()
    def lap_note(row):
        if row["IsPitLap"]:
            return "PIT"
        return ""
    df["LapNote"] = df.apply(lap_note, axis=1)
    laps[drv] = df

# Gap
ham = laps["HAM"][["LapNumber","LapTimeSec"]].rename(columns={"LapTimeSec":"HAM"})
rus = laps["RUS"][["LapNumber","LapTimeSec"]].rename(columns={"LapTimeSec":"RUS"})
merged = pd.merge(ham, rus, on="LapNumber", how="inner")
merged["HAM_cum"] = merged["HAM"].cumsum()
merged["RUS_cum"] = merged["RUS"].cumsum()
merged["Gap"]     = merged["RUS_cum"] - merged["HAM_cum"]

# Figure
fig = make_subplots(
    rows=3, cols=1,
    subplot_titles=[
        "Lap Times — all laps (pit annotated)",
        "Gap: Russell vs Hamilton  (+ = Russell behind)",
        "Tyre Stint Map",
    ],
    vertical_spacing=0.10,
    row_heights=[0.38, 0.35, 0.27],
)

# VSC/SC band helper
def add_status_bands(row):
    for start, end, kind in all_bands:
        color = YELLOW if kind == "VSC" else ORANGE
        # add_shape rect respects row/col properly unlike add_vrect in subplots
        fig.add_shape(
            type="rect",
            x0=start, x1=end,
            y0=0, y1=1,
            xref=f"x{row if row > 1 else ''}",
            yref=f"y{row if row > 1 else ''} domain",
            fillcolor=color, opacity=0.20,
            line_width=0,
            row=row, col=1,
        )
        for x in [start, end]:
            fig.add_shape(
                type="line",
                x0=x, x1=x, y0=0, y1=1,
                xref=f"x{row if row > 1 else ''}",
                yref=f"y{row if row > 1 else ''} domain",
                line=dict(color=color, width=1.5, dash="dot"),
                row=row, col=1,
            )

def add_status_labels(row, yref_domain):
    for start, end, kind in all_bands:
        color = YELLOW if kind == "VSC" else ORANGE
        fig.add_annotation(
            x=(start + end) / 2, y=1,
            yref=yref_domain,
            text=f"<b>{kind}</b>",
            showarrow=False,
            font=dict(color=color, size=8),
            yshift=-2, row=row, col=1,
        )

# Panel 1: Lap times
add_status_bands(1)
add_status_labels(1, "y domain")

# Driver lines
for drv, cfg in DRIVERS.items():
    df = laps[drv]
    fig.add_trace(go.Scatter(
        x=df["LapNumber"], y=df["LapTimeSec"],
        mode="lines", name=cfg["label"],
        line=dict(color=cfg["color"], width=1.8),
        legendgroup=drv,
        legendrank=1 if drv == "HAM" else 3,
        hovertemplate=(
            f"<b>{cfg['label']}</b><br>"
            "Lap %{x:.0f}<br>Time: %{y:.3f}s<br>%{customdata}<extra></extra>"
        ),
        customdata=df["LapNote"],
    ), row=1, col=1)

# Pit markers
for drv, cfg in DRIVERS.items():
    df  = laps[drv]
    pit = df[df["IsPitLap"]]
    fig.add_trace(go.Scatter(
        x=pit["LapNumber"], y=pit["LapTimeSec"],
        mode="markers",
        name="Pit stop",
        marker=dict(symbol="circle", size=8,
                    color=cfg["color"], line=dict(color="white", width=1.5)),
        legendgroup="pit",
        legendrank=2 if drv == "HAM" else 4,
        showlegend=True,
        hovertemplate=(
            f"<b>{cfg['label']} — PIT</b><br>"
            "Lap %{x:.0f}<br>Time: %{y:.3f}s<extra></extra>"
        ),
    ), row=1, col=1)

fig.update_yaxes(title_text="Lap Time (s)", row=1, col=1)
fig.update_xaxes(title_text="Lap", row=1, col=1)

# Panel 2: Gap
add_status_bands(2)
add_status_labels(2, "y2 domain")

fig.add_trace(go.Scatter(
    x=merged["LapNumber"], y=merged["Gap"],
    mode="lines",
    line=dict(color=DRIVERS["RUS"]["color"], width=2),
    fill="tozeroy", fillcolor="rgba(39,244,210,0.10)",
    showlegend=False,
    hovertemplate="Lap %{x:.0f}<br>Gap: %{y:+.2f}s<extra></extra>",
), row=2, col=1)

fig.add_trace(go.Scatter(
    x=[merged["LapNumber"].iloc[0], merged["LapNumber"].iloc[-1]],
    y=[0, 0],
    mode="lines",
    line=dict(color=DRIVERS["HAM"]["color"], width=1.5, dash="dash"),
    opacity=0.7,
    showlegend=False,
    hoverinfo="skip",
), row=2, col=1)

final_gap = merged["Gap"].iloc[-1]
final_lap = merged["LapNumber"].iloc[-1]
fig.add_annotation(
    x=final_lap, y=final_gap,
    text=f"<b>Final gap: +{final_gap:.1f}s</b>",
    showarrow=True, arrowhead=2,
    arrowcolor=DRIVERS["RUS"]["color"],
    font=dict(color=DRIVERS["RUS"]["color"], size=11),
    bgcolor="rgba(13,13,13,0.8)",
    bordercolor=DRIVERS["RUS"]["color"],
    borderwidth=1,
    ax=-120, ay=-30, row=2, col=1,
)

fig.update_yaxes(title_text="Gap (s)", row=2, col=1)
fig.update_xaxes(title_text="Lap", row=2, col=1)

# Panel 3: Stint map
driver_list = list(DRIVERS.keys())

for d_idx, drv in enumerate(driver_list):
    df = laps[drv]
    for _, stint_df in df.groupby("Stint"):
        compound = str(stint_df["Compound"].iloc[0]).upper()
        start    = stint_df["LapNumber"].iloc[0]
        end      = stint_df["LapNumber"].iloc[-1]
        color    = TIRE_COLORS.get(compound, "#888")
        width    = end - start + 1
        fig.add_shape(
            type="rect",
            x0=start - 0.4, x1=end + 0.4,
            y0=d_idx - 0.38, y1=d_idx + 0.38,
            fillcolor=color, opacity=0.85,
            line=dict(width=0),
            row=3, col=1,
        )
        if width > 3:
            fig.add_annotation(
                x=(start + end) / 2, y=d_idx,
                text=f"<b>{compound[0]}  L{int(start)}–{int(end)}</b>",
                showarrow=False, font=dict(size=9, color="#111"),
                row=3, col=1,
            )

for start, end, kind in all_bands:
    color = YELLOW if kind == "VSC" else ORANGE
    fig.add_shape(
        type="rect",
        x0=start, x1=end,
        y0=0, y1=1,
        xref="x3", yref="y3 domain",
        fillcolor=color, opacity=0.25,
        line_width=0,
        row=3, col=1,
    )
    for x in [start, end]:
        fig.add_shape(
            type="line",
            x0=x, x1=x, y0=0, y1=1,
            xref="x3", yref="y3 domain",
            line=dict(color=color, width=1.5, dash="dot"),
            row=3, col=1,
        )
    fig.add_annotation(
        x=(start + end) / 2,
        y=len(driver_list) - 0.55,
        text=f"<b>{kind}</b>",
        showarrow=False,
        font=dict(color=color, size=8),
        row=3, col=1,
    )

fig.update_yaxes(
    tickvals=list(range(len(driver_list))),
    ticktext=[f"<b>{DRIVERS[d]['label']}</b>" for d in driver_list],
    row=3, col=1,
)
fig.update_xaxes(title_text="Lap", row=3, col=1)
fig.update_yaxes(zeroline=False, row=3, col=1)

# Tire legend
for i, (comp, color) in enumerate(TIRE_COLORS.items()):
    fig.add_annotation(
        x=0.01 + i * 0.07,
        y=-0.045,
        xref="paper", yref="paper",
        text=f"<span style='color:{color}'>&#9632;</span> {comp.capitalize()}",
        showarrow=False,
        font=dict(size=9, color=TEXT),
        xanchor="left",
    )

# Global styling
fig.update_layout(
    title=dict(
        text=(
            "<b>2026 Spanish Grand Prix — Hamilton vs Russell</b>"
            "<br><sup>Real data via FastF1  |  "
            "HAM: Soft→Hard→Medium→Hard (3 stops)  |  "
            "RUS: Medium→Hard→Hard (2 stops)  |  "
            "Yellow = VSC"
        ),
        font=dict(size=15, color="white"),
        x=0.01, xanchor="left",
    ),
    paper_bgcolor=BG, plot_bgcolor=PANEL,
    font=dict(color=TEXT, family="Inter, system-ui, sans-serif", size=11),
    legend=dict(
        bgcolor="rgba(30,30,30,0.85)", bordercolor="#333", borderwidth=1,
        font=dict(size=11),
        orientation="h", x=0.01, y=1.02,
        traceorder="normal",
        itemwidth=30,
    ),
    height=950,
    margin=dict(t=100, b=60, l=70, r=30),
    hovermode="x unified",
)
for i in range(1, 4):
    fig.update_xaxes(gridcolor=GRID, gridwidth=1, showgrid=True, row=i, col=1)
    fig.update_yaxes(gridcolor=GRID, gridwidth=1, showgrid=True, row=i, col=1)

fig.show()
fig.write_html("barcelona_2026_HAMvsRUS_dashboard.html")
