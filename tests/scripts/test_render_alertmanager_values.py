from __future__ import annotations

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
