from __future__ import annotations

from scripts.render_alertmanager_values import DUMMY_URL, PLACEHOLDER, main, render


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
