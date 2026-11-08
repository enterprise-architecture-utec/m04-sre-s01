"""Dashboard ligero: agregaciones RED derivadas de los logs locales."""

import html
import json
import math
from collections import defaultdict
from pathlib import Path


def load_records(data_dir):
    path = Path(data_dir) / "requests.jsonl"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p / 100 * len(ordered)) - 1)]


def summarize(records):
    count = len(records)
    errors = sum(r["status"] >= 500 for r in records)
    values = [r["latency_ms"] for r in records]
    return {
        "requests": count,
        "errors": errors,
        "error_rate": errors * 100 / count if count else 0,
        "p50": percentile(values, 50),
        "p90": percentile(values, 90),
        "p99": percentile(values, 99),
    }


def bar_chart(title, labels_and_values, suffix=""):
    pairs = list(labels_and_values)
    maximum = max((value for _, value in pairs), default=0) or 1
    rows = []
    for label, value in pairs:
        width = 400 * value / maximum
        rows.append(
            f'<div class="row"><span>{html.escape(str(label))}</span>'
            f'<svg viewBox="0 0 400 20" role="img" aria-label="{value:.1f}{suffix}">'
            f'<rect width="{width:.2f}" height="20" fill="#087e8b"/></svg>'
            f'<b>{value:.1f}{suffix}</b></div>'
        )
    return f"<section><h2>{html.escape(title)}</h2>{''.join(rows) or '<p>Sin datos.</p>'}</section>"


def render(data_dir):
    records = load_records(data_dir)
    totals = summarize(records)
    minutes = defaultdict(list)
    latencies = defaultdict(list)
    for record in records:
        minutes[record["timestamp"][:16]].append(record)
        latencies[record["path"]].append(record["latency_ms"])
    p = lambda key: f'{totals[key]:.2f} ms' if totals[key] is not None else "sin datos"
    cards = (
        f'<p><b>Solicitudes:</b> {totals["requests"]} &nbsp; '
        f'<b>Errores 5xx:</b> {totals["errors"]} ({totals["error_rate"]:.1f}%) &nbsp; '
        f'<b>p50:</b> {p("p50")} &nbsp; <b>p90:</b> {p("p90")} &nbsp; <b>p99:</b> {p("p99")}</p>'
    )
    charts = bar_chart("Solicitudes por minuto UTC",
                       sorted((minute, len(items)) for minute, items in minutes.items()))
    charts += bar_chart("Tasa de errores 5xx por minuto UTC (%)",
                        sorted((minute, summarize(items)["error_rate"])
                               for minute, items in minutes.items()), "%")
    charts += bar_chart("Percentiles de latencia global (ms)",
                        [(key, totals[key]) for key in ("p50", "p90", "p99")
                         if totals[key] is not None], " ms")
    charts += bar_chart(
        "Latencia media por ruta (ms)",
        sorted((path, sum(values) / len(values)) for path, values in latencies.items()),
        " ms",
    )
    return (
        '<!doctype html><html lang="es"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width">'
        '<title>Observabilidad local</title><style>body{font:16px sans-serif;max-width:950px;'
        'margin:2em auto;padding:0 1em;color:#18323a}section{border:1px solid #ccc;'
        'padding:1em;margin:1em 0}.row{display:grid;grid-template-columns:150px 1fr 90px;'
        'gap:1em;align-items:center;margin:.5em 0}svg{width:100%;height:20px}</style>'
        '<h1>Observabilidad local — datos simulados</h1>'
        '<p>Agregados de logs locales; actualiza la página para ver nuevas solicitudes. '
        'Los percentiles con pocas muestras son inestables.</p>'
        + cards + charts + "</html>"
    )
