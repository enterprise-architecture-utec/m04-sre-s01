import json
import sys
import textwrap
import types
from pathlib import Path

import pytest


@pytest.fixture
def aws_handler(monkeypatch):
    template = Path("aws/template.yaml").read_text(encoding="utf-8")
    source = template.split("        ZipFile: |\n", 1)[1].split("\n  Api:\n", 1)[0]
    source = textwrap.dedent(source)
    calls = []
    client = types.SimpleNamespace(put_metric_data=lambda **kwargs: calls.append(kwargs))
    monkeypatch.setitem(sys.modules, "boto3", types.SimpleNamespace(client=lambda service: client))
    monkeypatch.setenv("APP_NAME", "payment-lambda-equipo-01")
    monkeypatch.setenv("METRIC_NAMESPACE", "LabObservabilidad/equipo-01")
    namespace = {}
    exec(compile(source, "lambda_inline.py", "exec"), namespace)
    return namespace["handler"], calls


def event(path, method="GET"):
    return {"rawPath": path, "requestContext": {"http": {"method": method}}}


def test_aws_controlled_http_error_publishes_application_metric(aws_handler, capsys):
    handler, calls = aws_handler
    response = handler(event("/error"), types.SimpleNamespace(aws_request_id="test-id"))
    assert response["statusCode"] == 500
    log = json.loads(capsys.readouterr().out)
    assert log["status"] == 500
    assert log["request_id"] == "test-id"
    assert calls[0]["Namespace"] == "LabObservabilidad/equipo-01"
    assert {m["MetricName"] for m in calls[0]["MetricData"]} == {"Http5xx", "RequestLatency"}
    assert calls[0]["MetricData"][1]["Dimensions"] == [
        {"Name": "AppName", "Value": "payment-lambda-equipo-01"}
    ]


def test_aws_exception_is_unhandled(aws_handler, capsys):
    handler, calls = aws_handler
    with pytest.raises(RuntimeError, match="controlled exception"):
        handler(event("/exception"), types.SimpleNamespace(aws_request_id="test-id"))
    assert json.loads(capsys.readouterr().out)["event_type"] == "unhandled_exception"
    assert not calls


def test_aws_health_and_payment(aws_handler):
    handler, calls = aws_handler
    ctx = types.SimpleNamespace(aws_request_id="test-id")
    assert handler(event("/health"), ctx)["statusCode"] == 200
    assert handler(event("/pay", "POST"), ctx)["statusCode"] == 200
    assert all([m["MetricName"] for m in call["MetricData"]] == ["RequestLatency"] for call in calls)
