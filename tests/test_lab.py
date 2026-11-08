import json
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from lab import app
from lab.dashboard import load_records, percentile, render, summarize


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "DATA_DIR", tmp_path)
    httpd = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}", tmp_path
    httpd.shutdown()
    thread.join()
    httpd.server_close()


def request(url, path, method="GET", headers=None):
    req = Request(url + path, method=method, headers=headers or {})
    try:
        with urlopen(req, timeout=5) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def test_endpoints_metrics_and_dashboard(server):
    url, data = server
    assert request(url, "/health")[0] == 200
    assert request(url, "/pay", "POST")[0] == 200
    assert request(url, "/slow")[0] == 200
    assert request(url, "/error")[0] == 500
    assert request(url, "/missing")[0] == 404
    records = load_records(data)
    summary = summarize(records)
    assert summary["requests"] == 5
    assert summary["errors"] == 1
    assert summary["error_rate"] == 20
    assert next(r for r in records if r["path"] == "/slow")["latency_ms"] >= 750
    assert request(url, "/dashboard")[0] == 200
    assert "Solicitudes por minuto UTC" in render(data)
    assert "Tasa de errores 5xx por minuto UTC" in render(data)
    assert "Percentiles de latencia global" in render(data)
    assert len(load_records(data)) == 5


def test_propagation_and_trace_log_correlation(server):
    url, data = server
    trace_id = "1234567890abcdef1234567890abcdef"
    parent_id = "1234567890abcdef"
    assert request(url, "/pay", "POST", {
        "Traceparent": f"00-{trace_id}-{parent_id}-01"
    })[0] == 200
    trace_file = data / "traces.jsonl"
    for _ in range(50):
        if trace_file.exists() and len(trace_file.read_text().splitlines()) >= 2:
            break
        time.sleep(0.01)
    spans = [json.loads(line) for line in trace_file.read_text().splitlines()]
    server_span = next(span for span in spans if span["name"] == "POST /pay")
    child = next(span for span in spans if span["name"] == "payment.check")
    assert server_span["trace_id"] == trace_id
    assert server_span["parent_span_id"] == parent_id
    assert child["parent_span_id"] == server_span["span_id"]
    assert load_records(data)[0]["trace_id"] == trace_id


def test_percentiles_and_empty_dashboard(tmp_path):
    assert percentile([], 99) is None
    assert [percentile([10, 20, 30, 40, 50], p) for p in (50, 90, 99)] == [30, 50, 50]
    assert "sin datos" in render(tmp_path)
