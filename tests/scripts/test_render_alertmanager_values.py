from __future__ import annotations

import yaml

from scripts.render_alertmanager_values import (
    CLUSTER_PLACEHOLDER,
    DEFAULT_CLUSTER_LABEL,
    DUMMY_URL,
    PLACEHOLDER,
    main,
    render,
)


def test_render_substitutes_forwarder_url():
    text = f'url: "{PLACEHOLDER}"\n'
    assert (
        render(text, "https://forwarder.example/api?code=abc")
        == 'url: "https://forwarder.example/api?code=abc"\n'
    )


def test_render_substitutes_dummy_url_when_empty():
    text = f'url: "{PLACEHOLDER}"\n'
    assert render(text, "") == f'url: "{DUMMY_URL}"\n'


def test_render_replaces_every_occurrence():
    text = f"a: {PLACEHOLDER}\nb: {PLACEHOLDER}\n"
    assert render(text, "https://x") == "a: https://x\nb: https://x\n"


def test_main_writes_rendered_values_to_stdout(tmp_path, capsys):
    values_file = tmp_path / "values.yaml"
    values_file.write_text(f'url: "{PLACEHOLDER}"\n')

    exit_code = main([str(values_file), "--forwarder-url", "https://forwarder.example/api"])

    assert exit_code == 0
    assert capsys.readouterr().out == 'url: "https://forwarder.example/api"\n'


def test_main_defaults_to_dummy_url(tmp_path, capsys):
    values_file = tmp_path / "values.yaml"
    values_file.write_text(f'url: "{PLACEHOLDER}"\n')

    main([str(values_file)])

    assert capsys.readouterr().out == f'url: "{DUMMY_URL}"\n'


def test_render_substitutes_the_per_run_cluster_label():
    text = f'cluster: "{CLUSTER_PLACEHOLDER}"\nurl: "{PLACEHOLDER}"\n'
    out = render(text, "https://f.example/x", "kind-gha-123")
    assert 'cluster: "kind-gha-123"' in out and CLUSTER_PLACEHOLDER not in out


def test_render_defaults_the_cluster_label():
    text = f'cluster: "{CLUSTER_PLACEHOLDER}"\n'
    assert render(text, "") == f'cluster: "{DEFAULT_CLUSTER_LABEL}"\n'


def test_real_values_file_has_no_placeholders_after_render():
    from pathlib import Path

    rendered = render(
        Path("deploy/helm/values/kube-prometheus-stack.yaml").read_text(encoding="utf-8"),
        "https://f.example/x",
        "kind-gha-1",
    )
    assert "__" not in rendered.replace("__pycache__", "")


def test_real_values_file_has_no_placeholders_after_render_no_kafka():
    from pathlib import Path

    rendered = render(
        Path("deploy/helm/values/kube-prometheus-stack.yaml").read_text(encoding="utf-8"),
        "https://f.example/x",
        "kind-gha-1",
        kafka=False,
    )
    assert "__" not in rendered.replace("__pycache__", "")


def test_kafka_routing_sends_kafka_alerts_to_route_b_and_everything_else_to_route_a():
    from pathlib import Path

    rendered = render(
        Path("deploy/helm/values/kube-prometheus-stack.yaml").read_text(encoding="utf-8"),
        "https://f.example/x",
    )
    config = yaml.safe_load(rendered)["alertmanager"]["config"]

    assert config["route"]["receiver"] == "route-a-kafka"
    child_route = config["route"]["routes"][0]
    assert child_route["receiver"] == "route-b-forwarder"
    assert child_route["continue"] is False
    assert child_route["matchers"] == [
        'alertname =~ "KafkaBrokerDown|KafkaRelayLag|AlertsBridgeDown|KafkaRelayDown"'
    ]
    receiver_names = {r["name"] for r in config["receivers"]}
    assert receiver_names == {"route-a-kafka", "route-b-forwarder"}
    kafka_receiver = next(r for r in config["receivers"] if r["name"] == "route-a-kafka")
    assert (
        kafka_receiver["webhook_configs"][0]["url"]
        == "http://nordwind-bank-alerts-bridge.bank.svc:8080/alertmanager"
    )
    assert kafka_receiver["webhook_configs"][0]["send_resolved"] is True


def test_no_kafka_routing_sends_everything_to_route_b():
    from pathlib import Path

    rendered = render(
        Path("deploy/helm/values/kube-prometheus-stack.yaml").read_text(encoding="utf-8"),
        "https://f.example/x",
        kafka=False,
    )
    config = yaml.safe_load(rendered)["alertmanager"]["config"]

    assert config["route"]["receiver"] == "route-b-forwarder"
    assert "routes" not in config["route"]
    assert [r["name"] for r in config["receivers"]] == ["route-b-forwarder"]
    assert config["receivers"][0]["webhook_configs"][0]["url"] == "https://f.example/x"
