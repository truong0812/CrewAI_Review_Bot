"""Tests for kb_loader.py — Knowledge Base loading and formatting."""

import json
import os
import tempfile

import pytest

from kb_loader import (
    _build_conventions,
    _build_dependencies,
    _build_risks,
    _build_summaries,
    _validate_kb_schema,
    load_knowledge_base,
)


def _make_kb_data(**overrides):
    """Build a minimal valid KB JSON structure."""
    data = {
        "files": [
            {"file_id": "f1", "path": "src/main.py"},
            {"file_id": "f2", "path": "src/utils.py"},
        ],
        "modules": [{"module_id": "m1", "name": "core"}],
        "conventions": [
            {"name": "PEP 8", "description": "Follow PEP 8 style guide"},
        ],
        "risks": [
            {"name": "SQL Injection", "severity": "high", "file_path": "src/db.py"},
        ],
        "relations": [
            {"relation_type": "imports", "source_id": "f1", "target_id": "f2",
             "source_type": "File", "target_type": "File"},
        ],
        "summaries": [
            {"level": "file", "target_type": "file", "target_id": "f1",
             "content": "Main entry point"},
        ],
    }
    data.update(overrides)
    return data


def _write_kb_file(tmpdir, data):
    """Write a KB latest.json file and return the directory path."""
    kb_dir = os.path.join(tmpdir, "kb")
    os.makedirs(kb_dir, exist_ok=True)
    with open(os.path.join(kb_dir, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(data, f)
    return kb_dir


# ============================================================
# load_knowledge_base — integration
# ============================================================


class TestLoadKnowledgeBase:
    def test_loads_valid_kb(self, tmp_path):
        kb_dir = _write_kb_file(str(tmp_path), _make_kb_data())
        result = load_knowledge_base(kb_dir)
        assert "Project Knowledge Base" in result
        assert "PEP 8" in result
        assert "SQL Injection" in result

    def test_empty_path_returns_empty(self):
        assert load_knowledge_base("") == ""

    def test_none_path_returns_empty(self):
        assert load_knowledge_base(None) == ""

    def test_missing_file_returns_empty(self, tmp_path):
        result = load_knowledge_base(str(tmp_path))
        assert result == ""

    def test_invalid_json_returns_empty(self, tmp_path):
        kb_dir = os.path.join(str(tmp_path), "kb")
        os.makedirs(kb_dir)
        with open(os.path.join(kb_dir, "latest.json"), "w") as f:
            f.write("{invalid json")
        result = load_knowledge_base(kb_dir)
        assert result == ""

    def test_truncation_at_max_chars(self, tmp_path):
        data = _make_kb_data()
        data["conventions"] = [
            {"name": f"Conv {i}", "description": "X" * 500}
            for i in range(50)
        ]
        kb_dir = _write_kb_file(str(tmp_path), data)
        result = load_knowledge_base(kb_dir, max_chars=500)
        assert len(result) <= 600  # margin for truncation notice
        assert "truncated" in result

    def test_empty_data_returns_empty(self, tmp_path):
        data = {"files": []}
        kb_dir = _write_kb_file(str(tmp_path), data)
        result = load_knowledge_base(kb_dir)
        assert result == ""

    def test_priority_order_conventions_before_summaries(self, tmp_path):
        data = _make_kb_data()
        kb_dir = _write_kb_file(str(tmp_path), data)
        result = load_knowledge_base(kb_dir)
        conv_pos = result.index("Coding Conventions")
        risk_pos = result.index("Risk Areas")
        summary_pos = result.index("File Summaries")
        assert conv_pos < risk_pos < summary_pos


# ============================================================
# _validate_kb_schema
# ============================================================


class TestValidateKbSchema:
    def test_valid_schema(self):
        assert _validate_kb_schema({"files": []}) is True

    def test_not_dict(self):
        assert _validate_kb_schema("string") is False
        assert _validate_kb_schema([1, 2]) is False

    def test_missing_files_key(self):
        assert _validate_kb_schema({"conventions": []}) is False

    def test_files_not_list(self):
        assert _validate_kb_schema({"files": "not a list"}) is False


# ============================================================
# _build_conventions
# ============================================================


class TestBuildConventions:
    def test_builds_convention_items(self):
        conventions = [
            {"name": "Type Hints", "description": "Use type hints everywhere"},
            {"name": "PEP 8", "description": "Follow PEP 8"},
        ]
        result = _build_conventions(conventions)
        assert "### Coding Conventions" in result
        assert "**Type Hints**" in result
        assert "**PEP 8**" in result

    def test_skips_items_without_name_or_desc(self):
        conventions = [
            {"name": "Valid", "description": "OK"},
            {"name": ""},
            {"description": "No name"},
        ]
        result = _build_conventions(conventions)
        assert "Valid" in result
        assert result.count("- **") == 1

    def test_empty_list_returns_empty(self):
        assert _build_conventions([]) == ""


# ============================================================
# _build_risks
# ============================================================


class TestBuildRisks:
    def test_builds_risk_items(self):
        risks = [
            {"name": "SQL Injection", "severity": "high", "file_path": "db.py"},
        ]
        result = _build_risks(risks)
        assert "### Risk Areas" in result
        assert "SQL Injection" in result
        assert "HIGH" in result
        assert "`db.py`" in result

    def test_risk_without_file_path(self):
        risks = [{"name": "Generic Risk", "severity": "medium"}]
        result = _build_risks(risks)
        assert "Generic Risk" in result
        assert "MEDIUM" in result
        assert "in `" not in result

    def test_unknown_severity_defaults(self):
        risks = [{"name": "Unknown Risk", "severity": "unknown"}]
        result = _build_risks(risks)
        assert "UNKNOWN" in result

    def test_none_severity_defaults_to_unknown(self):
        risks = [{"name": "Bad Risk", "severity": None}]
        result = _build_risks(risks)
        assert "UNKNOWN" in result

    def test_empty_list_returns_empty(self):
        assert _build_risks([]) == ""

    def test_skips_nameless_risks(self):
        risks = [{"severity": "high"}]
        result = _build_risks(risks)
        assert result == ""


# ============================================================
# _build_summaries
# ============================================================


class TestBuildSummaries:
    def test_builds_file_summaries(self):
        file_map = {"f1": "src/main.py"}
        summaries = [
            {"level": "file", "target_type": "file", "target_id": "f1", "content": "Main module"},
        ]
        result = _build_summaries(summaries, file_map)
        assert "### File Summaries" in result
        assert "**src/main.py**" in result
        assert "Main module" in result

    def test_skips_non_file_level_summaries(self):
        summaries = [
            {"level": "module", "target_type": "module", "content": "Module summary"},
        ]
        result = _build_summaries(summaries, {})
        assert result == ""

    def test_skips_kb_internal_files(self):
        file_map = {"f1": "knowledge_base/generated.txt"}
        summaries = [
            {"level": "file", "target_type": "file", "target_id": "f1", "content": "KB file"},
        ]
        result = _build_summaries(summaries, file_map)
        assert result == ""

    def test_truncates_long_summaries(self):
        file_map = {"f1": "big.py"}
        summaries = [
            {"level": "file", "target_type": "file", "target_id": "f1",
             "content": "X" * 200},
        ]
        result = _build_summaries(summaries, file_map)
        assert "..." in result
        assert len(result.split("big.py")[1]) < 200

    def test_empty_content_skipped(self):
        file_map = {"f1": "empty.py"}
        summaries = [
            {"level": "file", "target_type": "file", "target_id": "f1", "content": "  "},
        ]
        result = _build_summaries(summaries, file_map)
        assert result == ""


# ============================================================
# _build_dependencies
# ============================================================


class TestBuildDependencies:
    def test_builds_import_relation(self):
        file_map = {"f1": "main.py", "f2": "utils.py"}
        module_map = {}
        relations = [
            {"relation_type": "imports", "source_id": "f1", "target_id": "f2",
             "source_type": "File", "target_type": "File"},
        ]
        result = _build_dependencies(relations, file_map, module_map)
        assert "### Module Dependencies" in result
        assert "`main.py`" in result
        assert "`utils.py`" in result

    def test_builds_depends_on_relation(self):
        file_map = {"f1": "a.py", "f2": "b.py"}
        relations = [
            {"relation_type": "depends_on", "source_id": "f1", "target_id": "f2",
             "source_type": "File", "target_type": "File"},
        ]
        result = _build_dependencies(relations, file_map, {})
        assert "depends on" in result

    def test_skips_non_file_relations(self):
        relations = [
            {"relation_type": "imports", "source_id": "m1", "target_id": "m2",
             "source_type": "Module", "target_type": "Module"},
        ]
        result = _build_dependencies(relations, {}, {})
        assert result == ""

    def test_skips_kb_internal_references(self):
        file_map = {"f1": "main.py", "f2": "knowledge_base/kb.py"}
        relations = [
            {"relation_type": "imports", "source_id": "f1", "target_id": "f2",
             "source_type": "File", "target_type": "File"},
        ]
        result = _build_dependencies(relations, file_map, {})
        assert result == ""

    def test_skips_unknown_relation_types(self):
        relations = [
            {"relation_type": "documents", "source_id": "f1", "target_id": "f2",
             "source_type": "File", "target_type": "File"},
        ]
        result = _build_dependencies(relations, {}, {})
        assert result == ""
