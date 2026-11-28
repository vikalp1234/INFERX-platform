import json
import re
from pathlib import Path

NOTEBOOK_DIR = Path(__file__).resolve().parents[2] / "notebooks"
FORBIDDEN = (re.compile(r"HF_TOKEN\s*="), re.compile(r"hf_[A-Za-z0-9]{20,}"), re.compile("/Users/"))


def _notebooks():
    return sorted(NOTEBOOK_DIR.glob("*.ipynb"))


def test_at_least_one_notebook_exists():
    assert _notebooks()


def test_notebooks_have_no_outputs_or_secrets():
    for path in _notebooks():
        text = path.read_text()
        nb = json.loads(text)
        for cell in nb["cells"]:
            if cell["cell_type"] == "code":
                assert cell["outputs"] == [], path.name
                assert cell["execution_count"] is None, path.name
        for pattern in FORBIDDEN:
            assert not pattern.search(text), (path.name, pattern.pattern)
