"""Tráfico sintético reproducible; también se puede apuntar a la API AWS."""

import argparse
import json
from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--cycles", type=int, default=5)
    args = parser.parse_args()
    if args.cycles < 1:
        parser.error("--cycles debe ser positivo")
    counts = Counter()
    for _ in range(args.cycles):
        for path, method in [("/health", "GET"), ("/pay", "POST"),
                             ("/pay", "POST"), ("/slow", "GET"), ("/error", "GET")]:
            data = b'{"amount":100}' if method == "POST" else None
            request = Request(args.url.rstrip("/") + path, data=data, method=method,
                              headers={"Content-Type": "application/json"})
            try:
                with urlopen(request, timeout=15) as response:
                    status = response.status
            except HTTPError as exc:
                status = exc.code
            except URLError as exc:
                raise SystemExit(f"No se pudo conectar: {exc}") from exc
            counts[str(status)] += 1
    print(json.dumps({"simulated": True, "cycles": args.cycles, "http_statuses": counts}))


if __name__ == "__main__":
    main()
