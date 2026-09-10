from __future__ import annotations

import time

from bank.k8s._shared.kafka import ConsumerLoop, KafkaSettings


class FakeFaultFile:
    def __init__(self, mode: str | None = None) -> None:
        self.mode = mode

    def current(self) -> str | None:
        return self.mode


class FakeMessage:
    def __init__(self, value: bytes, error: object = None) -> None:
        self._value = value
        self._error = error

    def value(self) -> bytes:
        return self._value

    def error(self) -> object:
        return self._error


class FakeConsumer:
    def __init__(self, messages: list[FakeMessage] | None = None) -> None:
        self._messages = list(messages or [])
        self.poll_calls = 0
        self.committed: list[FakeMessage] = []

    def poll(self, timeout: float) -> FakeMessage | None:
        self.poll_calls += 1
        if self._messages:
            return self._messages.pop(0)
        return None

    def commit(self, message: FakeMessage | None = None, **kwargs: object) -> None:
        self.committed.append(message)


def test_from_env_returns_none_when_bootstrap_unset():
    assert KafkaSettings.from_env({}) is None


def test_from_env_builds_settings_from_the_four_env_vars():
    env = {
        "KAFKA_BOOTSTRAP": "nordwind-bank-kafka-bootstrap.bank.svc:9093",
        "KAFKA_USER": "cards-authorization",
        "KAFKA_PASSWORD_FILE": "/etc/nordwind/kafka/user/password",
        "KAFKA_CA_FILE": "/etc/nordwind/kafka/ca/ca.crt",
    }
    settings = KafkaSettings.from_env(env)

    assert settings == KafkaSettings(
        bootstrap="nordwind-bank-kafka-bootstrap.bank.svc:9093",
        user="cards-authorization",
        password_file="/etc/nordwind/kafka/user/password",  # noqa: S106 - a path, not a secret
        ca_file="/etc/nordwind/kafka/ca/ca.crt",
    )


def test_client_config_reads_password_file_and_sets_sasl_ssl_scram(tmp_path):
    password_file = tmp_path / "password"
    password_file.write_text("s3cret\n")
    settings = KafkaSettings(
        bootstrap="broker:9093",
        user="cards-authorization",
        password_file=str(password_file),
        ca_file="/etc/nordwind/kafka/ca/ca.crt",
    )

    config = settings.client_config()

    assert config == {
        "bootstrap.servers": "broker:9093",
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "SCRAM-SHA-512",
        "sasl.username": "cards-authorization",
        "sasl.password": "s3cret",
        "ssl.ca.location": "/etc/nordwind/kafka/ca/ca.crt",
    }


def test_consumer_loop_pauses_when_pause_mode_is_active():
    fault_file = FakeFaultFile("lag")
    consumer = FakeConsumer([FakeMessage(b'{"txn_id": "a"}')])
    handled = []
    loop = ConsumerLoop(
        consumer,
        lambda c, m: handled.append(m),
        fault_file=fault_file,
        pause_mode="lag",
        poll_timeout=0.02,
    )

    loop.start()
    time.sleep(0.1)
    loop.stop()

    assert consumer.poll_calls == 0
    assert handled == []


def test_consumer_loop_resumes_once_pause_mode_clears():
    fault_file = FakeFaultFile("lag")
    consumer = FakeConsumer([FakeMessage(b'{"txn_id": "a"}')])
    handled = []
    loop = ConsumerLoop(
        consumer,
        lambda c, m: handled.append(m),
        fault_file=fault_file,
        pause_mode="lag",
        poll_timeout=0.02,
    )

    loop.start()
    time.sleep(0.05)
    fault_file.mode = None
    time.sleep(0.1)
    loop.stop()

    assert len(handled) == 1


def test_consumer_loop_skips_error_messages_without_calling_handler():
    consumer = FakeConsumer([FakeMessage(b"", error="boom")])
    handled = []
    loop = ConsumerLoop(consumer, lambda c, m: handled.append(m), poll_timeout=0.02)

    loop.start()
    time.sleep(0.05)
    loop.stop()

    assert handled == []
