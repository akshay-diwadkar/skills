import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "skills" / "engineering" / "plan-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
from _plan_utils import Diagnostic, strip_fenced_code_blocks  # noqa: E402


class TestDiagnostic:
    def test_creates_with_code_and_message(self):
        d = Diagnostic(code="test.code", message="test message")
        assert d.code == "test.code"
        assert d.message == "test message"
        assert d.line is None
        assert d.is_warning is False

    def test_creates_with_all_fields(self):
        d = Diagnostic(code="test.code", message="test msg", line=5, is_warning=True)
        assert d.line == 5
        assert d.is_warning is True

    def test_to_dict(self):
        d = Diagnostic(code="tc", message="msg", line=3, is_warning=True)
        assert d.to_dict() == {"code": "tc", "message": "msg", "line": 3, "is_warning": True}

    def test_to_dict_no_line(self):
        d = Diagnostic(code="tc", message="msg")
        assert d.to_dict() == {"code": "tc", "message": "msg", "line": None, "is_warning": False}

    def test_str_error(self):
        d = Diagnostic(code="ec", message="err msg", line=10)
        assert str(d) == "Error [ec] on line 10: err msg"

    def test_str_warning(self):
        d = Diagnostic(code="wc", message="warn msg", line=3, is_warning=True)
        assert str(d) == "Warning [wc] on line 3: warn msg"

    def test_str_no_line(self):
        d = Diagnostic(code="nc", message="no line")
        assert str(d) == "Error [nc]: no line"


class TestStripFencedCodeBlocks:
    def test_no_code_blocks(self):
        text = "Some text\n## Heading\nMore text"
        assert strip_fenced_code_blocks(text) == text

    def test_strips_content_inside_fence(self):
        text = "Outside\n```\nInside\n```\nOutside again"
        expected = "Outside\n\n\n\nOutside again"
        assert strip_fenced_code_blocks(text) == expected

    def test_empty_fence(self):
        text = "Before\n```\n```\nAfter"
        expected = "Before\n\n\nAfter"
        assert strip_fenced_code_blocks(text) == expected

    def test_multiple_fences(self):
        text = "A\n```\nB\n```\nC\n```\nD\n```\nE"
        expected = "A\n\n\n\nC\n\n\n\nE"
        assert strip_fenced_code_blocks(text) == expected

    def test_unclosed_fence_treats_rest_as_code(self):
        text = "Start\n```\nStill code"
        expected = "Start\n\n"
        result = strip_fenced_code_blocks(text)
        assert result == expected

    def test_fence_with_language_tag(self):
        text = "A\n```python\nx = 1\n```\nB"
        expected = "A\n\n\n\nB"
        assert strip_fenced_code_blocks(text) == expected

    def test_indented_fence(self):
        text = "A\n  ```\n  code\n  ```\nB"
        expected_lines = strip_fenced_code_blocks(text).splitlines()
        assert "  code" not in expected_lines
        assert expected_lines[0] == "A"
        assert expected_lines[-1] == "B"

    def test_tilde_fence(self):
        text = "A\n~~~python\nx = 1\n~~~\nB"
        assert strip_fenced_code_blocks(text) == "A\n\n\n\nB"
