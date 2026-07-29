from __future__ import annotations

import hashlib
import importlib.util
import socket
import urllib.request
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]
TOKENIZER_DIR = (
    ROOT
    / "skills"
    / "engineering"
    / "map-codebase"
    / "scripts"
    / "tokenizer"
)
LOADER_PATH = TOKENIZER_DIR / "__init__.py"
EXPECTED_SHA256 = "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "map_codebase_tokenizer",
        LOADER_PATH,
        submodule_search_locations=[str(TOKENIZER_DIR)],
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_vendored_cl100k_base_exists_next_to_loader() -> None:
    module = _module()

    assert module.BPE_PATH.parent == LOADER_PATH.parent
    assert module.BPE_PATH.is_file()


def test_vendored_cl100k_base_has_expected_sha256() -> None:
    module = _module()

    assert hashlib.sha256(module.BPE_PATH.read_bytes()).hexdigest() == EXPECTED_SHA256


def test_building_encoding_never_touches_network(monkeypatch) -> None:
    def block_network(*_args, **_kwargs):
        raise AssertionError("offline tokenizer must not use the network")

    monkeypatch.setattr(socket, "create_connection", block_network)
    monkeypatch.setattr(urllib.request, "urlopen", block_network)
    module = _module()
    module.get_cl100k_base_encoding.cache_clear()

    encoding = module.get_cl100k_base_encoding()

    assert encoding.name == "cl100k_base"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", 0),
        ("abcde", 2),
        ("hello world", 2),
    ],
)
def test_known_token_counts(text: str, expected: int) -> None:
    module = _module()

    assert module.count_tokens(text) == expected


def test_encode_decode_round_trip() -> None:
    module = _module()
    text = "नमस्ते, world 🌍\nreturn value + 1"
    encoding = module.get_cl100k_base_encoding()

    assert encoding.decode(encoding.encode(text)) == text


def test_corrupted_ranks_are_rejected(tmp_path: Path) -> None:
    module = _module()
    corrupted = tmp_path / "cl100k_base.tiktoken"
    contents = bytearray(module.BPE_PATH.read_bytes())
    contents[-1] ^= 1
    corrupted.write_bytes(contents)

    with pytest.raises(
        RuntimeError,
        match=r"failed SHA-256 verification: expected [0-9a-f]{64}, got [0-9a-f]{64}",
    ):
        module._load_cl100k_base_encoding(corrupted)
