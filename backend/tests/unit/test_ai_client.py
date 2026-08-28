from types import SimpleNamespace

from app.ai.client import call_json


def _response():
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text='{"ok": true}')],
        usage=SimpleNamespace(input_tokens=2, output_tokens=3),
    )


def test_call_json_omits_temperature_when_sdk_does_not_support_it():
    class Messages:
        def __init__(self):
            self.called = False

        def create(self, *, model, system, messages, max_tokens):
            self.called = True
            return _response()

    messages = Messages()
    client = SimpleNamespace(messages=messages)

    result = call_json(
        client,
        model="test-model",
        system="system",
        user="user",
        max_tokens=20,
        temperature=0.2,
    )

    assert messages.called
    assert result.data == {"ok": True}


def test_call_json_keeps_temperature_for_compatible_clients():
    class Messages:
        def __init__(self):
            self.temperature = None

        def create(self, **kwargs):
            self.temperature = kwargs.get("temperature")
            return _response()

    messages = Messages()
    client = SimpleNamespace(messages=messages)

    call_json(
        client,
        model="test-model",
        system="system",
        user="user",
        max_tokens=20,
        temperature=0.3,
    )

    assert messages.temperature == 0.3
