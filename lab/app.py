"""API local con logs JSON y trazas OpenTelemetry, sin servicios externos."""

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from opentelemetry import context, propagate, trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace import SpanKind, Status, StatusCode

DATA_DIR = Path(os.environ.get("LAB_DATA_DIR", "data"))
LOCK = threading.Lock()


def append_json(filename, record):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK, (DATA_DIR / filename).open("a", encoding="utf-8") as output:
        output.write(json.dumps(record, ensure_ascii=False) + "\n")


class JsonSpanExporter(SpanExporter):
    def export(self, spans):
        for span in spans:
            append_json("traces.jsonl", {
                "name": span.name,
                "trace_id": format(span.context.trace_id, "032x"),
                "span_id": format(span.context.span_id, "016x"),
                "parent_span_id": format(span.parent.span_id, "016x") if span.parent else None,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "status": span.status.status_code.name,
                "attributes": dict(span.attributes),
            })
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(JsonSpanExporter()))
tracer = provider.get_tracer("lab.payment")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch()

    def dispatch(self):
        path = self.path.split("?", 1)[0]
        if path == "/dashboard" and self.command == "GET":
            from lab.dashboard import render
            self.send_body(200, render(DATA_DIR).encode(), "text/html; charset=utf-8")
            return

        parent = propagate.extract({key.lower(): value for key, value in self.headers.items()})
        token = context.attach(parent)
        try:
            with tracer.start_as_current_span(
                f"{self.command} {path}", kind=SpanKind.SERVER
            ) as span:
                started = time.perf_counter()
                request_id = str(uuid.uuid4())
                status = 200
                event = "request"
                if path == "/health" and self.command == "GET":
                    body = {"status": "ok"}
                elif path == "/pay" and self.command == "POST":
                    with tracer.start_as_current_span("payment.check"):
                        time.sleep(0.03)
                    body = {"status": "paid", "simulated": True}
                elif path == "/slow" and self.command == "GET":
                    with tracer.start_as_current_span("payment.slow_dependency"):
                        time.sleep(0.8)
                    body = {"status": "ok", "simulated": True}
                    event = "slow_response"
                elif path == "/error" and self.command == "GET":
                    status = 500
                    body = {"error": "controlled failure", "simulated": True}
                    event = "forced_error"
                    span.set_status(Status(StatusCode.ERROR))
                else:
                    status = 404
                    body = {"error": "not found"}
                latency = round((time.perf_counter() - started) * 1000, 2)
                span.set_attribute("http.request.method", self.command)
                span.set_attribute("url.path", path)
                span.set_attribute("http.response.status_code", status)
                span.set_attribute("request.id", request_id)
                append_json("requests.jsonl", {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event_type": event,
                    "method": self.command,
                    "path": path,
                    "status": status,
                    "latency_ms": latency,
                    "request_id": request_id,
                    "trace_id": format(span.get_span_context().trace_id, "032x"),
                    "simulated": True,
                })
                self.send_body(status, json.dumps(body).encode(), "application/json")
        finally:
            context.detach(token)

    def send_body(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Los logs de acceso relevantes se guardan como JSON, no en stderr.
        return


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("API: http://127.0.0.1:8000 — dashboard: /dashboard", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        provider.shutdown()


if __name__ == "__main__":
    main()
