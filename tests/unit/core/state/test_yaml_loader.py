# tests/unit/core/state/test_yaml_loader.py

import pytest
import yaml

from engine.io.yaml_loader import (
    iter_yaml_documents,
    load_yaml_optional,
    load_yaml_required,
)


def _write(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


class TestLoadYamlRequired:
    def test_returns_parsed_dict(self, tmp_path):
        path = tmp_path / "x.yaml"
        _write(path, "a: 1\nb: [2, 3]\n")
        assert load_yaml_required(path) == {"a": 1, "b": [2, 3]}

    def test_returns_parsed_list(self, tmp_path):
        path = tmp_path / "x.yaml"
        _write(path, "- 1\n- 2\n")
        assert load_yaml_required(path) == [1, 2]

    def test_empty_file_returns_none(self, tmp_path):
        path = tmp_path / "x.yaml"
        _write(path, "")
        assert load_yaml_required(path) is None

    def test_missing_file_raises_with_path(self, tmp_path):
        path = tmp_path / "missing.yaml"
        with pytest.raises(FileNotFoundError) as exc:
            load_yaml_required(path)
        assert str(path) in str(exc.value)

    def test_invalid_yaml_raises_yaml_error(self, tmp_path):
        path = tmp_path / "bad.yaml"
        _write(path, "a: [1, 2\n")  # unclosed bracket
        with pytest.raises(yaml.YAMLError):
            load_yaml_required(path)


class TestLoadYamlOptional:
    def test_returns_parsed_dict(self, tmp_path):
        path = tmp_path / "x.yaml"
        _write(path, "k: v\n")
        assert load_yaml_optional(path) == {"k": "v"}

    def test_missing_file_returns_none(self, tmp_path):
        assert load_yaml_optional(tmp_path / "missing.yaml") is None

    def test_empty_file_returns_none(self, tmp_path):
        path = tmp_path / "x.yaml"
        _write(path, "")
        assert load_yaml_optional(path) is None

    def test_invalid_yaml_raises_yaml_error(self, tmp_path):
        path = tmp_path / "bad.yaml"
        _write(path, "a: [1, 2\n")
        with pytest.raises(yaml.YAMLError):
            load_yaml_optional(path)


class TestIterYamlDocuments:
    def test_iterates_multi_doc(self, tmp_path):
        path = tmp_path / "multi.yaml"
        _write(path, "id: a\n---\nid: b\n---\nid: c\n")
        docs = list(iter_yaml_documents(path))
        assert docs == [{"id": "a"}, {"id": "b"}, {"id": "c"}]

    def test_single_doc_yields_one(self, tmp_path):
        path = tmp_path / "single.yaml"
        _write(path, "id: only\n")
        assert list(iter_yaml_documents(path)) == [{"id": "only"}]

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError) as exc:
            list(iter_yaml_documents(tmp_path / "missing.yaml"))
        assert "missing.yaml" in str(exc.value)
