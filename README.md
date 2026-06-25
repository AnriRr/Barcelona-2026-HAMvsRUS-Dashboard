# 2026 Spanish GP — Strategy Dashboard

Interactive race strategy analysis for Hamilton (Ferrari) vs Russell (Mercedes) using real FastF1 data.

## View the dashboard

[Open Dashboard](https://AnriRr.github.io/Barcelona-2026-HAMvsRUS-Dashboard/barcelona_2026_HAMvsRUS_dashboard.html)

## Run it locally

```bash
pip install fastf1 pandas plotly
python barcelona_2026_HAMvsRUS.py
```

Opens in your browser automatically. First run downloads the session data into `./f1_cache/`.

## What it shows

- **Lap Times** — all laps with pit stops annotated
- **Gap** — cumulative time difference between the two drivers
- **Tyre Stint Map** — compound and lap range per stint with VSC periods highlighted
