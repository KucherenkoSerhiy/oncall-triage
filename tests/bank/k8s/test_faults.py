from __future__ import annotations

from bank.k8s._shared.faults import FaultFile


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


def test_missing_file_is_normal(tmp_path):
    fault_file = FaultFile(path=str(tmp_path / "does-not-exist"), ttl=5)
    assert fault_file.current() is None


def test_empty_file_is_normal(tmp_path):
    path = tmp_path / "fault"
    path.write_text("")
    fault_file = FaultFile(path=str(path), ttl=5)
    assert fault_file.current() is None


def test_known_mode_is_returned(tmp_path):
    path = tmp_path / "fault"
    path.write_text("timeouts")
    fault_file = FaultFile(path=str(path), ttl=5, valid_modes=("timeouts", "issuer-down"))
    assert fault_file.current() == "timeouts"


def test_unknown_mode_is_normal_and_warns_once(tmp_path, caplog):
    path = tmp_path / "fault"
    path.write_text("nonsense")
    clock = FakeClock()
    fault_file = FaultFile(path=str(path), ttl=5, valid_modes=("timeouts",), clock=clock)

    with caplog.at_level("WARNING"):
        assert fault_file.current() is None
        clock.now = 100
        assert fault_file.current() is None

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1


def test_ttl_caches_between_reads(tmp_path):
    path = tmp_path / "fault"
    path.write_text("timeouts")
    clock = FakeClock()
    fault_file = FaultFile(path=str(path), ttl=5, valid_modes=("timeouts",), clock=clock)

    assert fault_file.current() == "timeouts"

    path.write_text("")
    clock.now = 4.9
    assert fault_file.current() == "timeouts"  # still cached, file not re-read yet


def test_hot_reload_after_ttl_elapses(tmp_path):
    path = tmp_path / "fault"
    path.write_text("timeouts")
    clock = FakeClock()
    fault_file = FaultFile(path=str(path), ttl=5, valid_modes=("timeouts",), clock=clock)

    assert fault_file.current() == "timeouts"

    path.write_text("")
    clock.now = 5.0
    assert fault_file.current() is None
