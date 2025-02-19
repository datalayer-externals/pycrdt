import re

import pytest
from datalayer_pycrdt import Array, Doc, Map, Text

hello = "Hello"
world = ", World"
sir = " Sir"
punct = "!"


def test_iterate():
    doc = Doc()
    doc["text"] = text = Text("abc")
    assert [char for char in text] == ["a", "b", "c"]


def test_str():
    doc1 = Doc()
    text1 = Text()
    doc1["text"] = text1
    with doc1.transaction():
        text1 += hello
        with doc1.transaction():
            text1 += world
        text1 += punct

    assert str(text1) == hello + world + punct

    doc2 = Doc()
    array2 = Array()
    doc2["array"] = array2
    text2 = Text("val")
    map2 = Map({"key": text2})
    array2.append(map2)
    assert str(array2) == '[{"key":"val"}]'


def test_api():
    doc = Doc()
    text = Text(hello + punct)

    with pytest.raises(RuntimeError) as excinfo:
        text.integrated
    assert str(excinfo.value) == "Not integrated in a document yet"

    with pytest.raises(RuntimeError) as excinfo:
        text.doc
    assert str(excinfo.value) == "Not integrated in a document yet"

    assert text.is_prelim
    assert text.prelim == hello + punct
    assert not text.is_integrated

    doc["text"] = text
    assert str(text) == hello + punct
    text.insert(len(hello), world)
    assert str(text) == hello + world + punct
    text.clear()
    assert len(text) == 0
    text[:] = hello + world + punct
    assert str(text) == hello + world + punct
    text[len(hello) : len(hello) + len(world)] = sir
    assert str(text) == hello + sir + punct
    # single character replacement
    text[len(text) - 1] = "?"
    assert str(text) == hello + sir + "?"
    # deletion with only an index
    del text[len(text) - 1]
    assert str(text) == hello + sir
    # deletion of an arbitrary range
    del text[len(hello) : len(hello) + len(sir)]
    assert str(text) == hello
    # deletion with start index == range length
    text += str(text)
    del text[len(hello) : 2 * len(hello)]
    assert str(text) == hello
    # deletion with a range of 0
    del text[len(hello) : len(hello)]
    assert str(text) == hello
    assert "".join([char for char in text]) == hello
    assert "el" in text

    with pytest.raises(RuntimeError) as excinfo:
        del text["a"]
    assert str(excinfo.value) == "Index not supported: a"

    with pytest.raises(RuntimeError) as excinfo:
        text["a"] = "b"
    assert str(excinfo.value) == "Index not supported: a"

    with pytest.raises(RuntimeError) as excinfo:
        text[1] = "ab"
    assert str(excinfo.value) == "Single item assigned value must have a length of 1, not 2"


def test_to_py():
    doc = Doc()
    doc["text"] = text = Text(hello)
    assert text.to_py() == hello


def test_prelim():
    text = Text(hello)
    assert text.to_py() == hello


def test_slice():
    doc = Doc()
    doc["text"] = text = Text(hello)

    for i, c in enumerate(hello):
        assert text[i] == c

    with pytest.raises(RuntimeError) as excinfo:
        text[1::2] = "a"
    assert str(excinfo.value) == "Step not supported"

    with pytest.raises(RuntimeError) as excinfo:
        text[-1:] = "a"
    assert str(excinfo.value) == "Negative start not supported"

    with pytest.raises(RuntimeError) as excinfo:
        text[:-1] = "a"
    assert str(excinfo.value) == "Negative stop not supported"


def test_formatting():
    doc = Doc()
    doc["text"] = text = Text("")

    text.insert(0, "hello ")
    assert len(text) == len("hello "), str(text)
    text.insert(len(text), "world", {"bold": True})
    text.insert(len(text), "! I have formatting!", {})
    text.format(len("hello world! "), len("hello world! I have formatting!") + 1, {"font-size": 32})
    text.insert_embed(len(text), b"png blob", {"type": "image"})

    diff = text.diff()

    assert diff == [
        ("hello ", None),
        ("world", {"bold": True}),
        ("! ", None),
        ("I have formatting!", {"font-size": 32}),
        (bytearray(b"png blob"), {"type": "image"}),
    ]


def test_observe():
    doc = Doc()
    doc["text"] = text = Text()
    events = []

    def callback(event):
        nonlocal text
        with pytest.raises(RuntimeError) as excinfo:
            text += world
        assert (
            str(excinfo.value)
            == "Read-only transaction cannot be used to modify document structure"
        )
        events.append(event)

    sub = text.observe(callback)  # noqa: F841
    origin = "test-text"
    with doc.transaction(origin=origin):
        text += hello
    event = events[0]
    assert str(event.target) == hello
    assert str(event.delta) == f"[{{'insert': '{hello}'}}]"
    assert event.path == []
    assert event.transaction.origin == origin
    assert (
        re.match(
            r"{target: Hello, delta: \[{'insert': 'Hello'}\], path: \[\], transaction: <[\w\.]+ object at 0x[a-fA-F\d]+>}",
            str(event),
        )
        is not None
    ), "Event string representation"
