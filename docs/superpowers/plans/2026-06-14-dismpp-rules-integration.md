# Dism++ Rules Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add conservative Dism++ Data.xml rule support for file and directory cleanup scanning.

**Architecture:** Create a focused parser module that converts supported Dism++ XML entries into normalized cleanup candidates. Existing CleanerLogic owns safety filtering, backup, simulation, and deletion, so the parser will not delete anything.

**Tech Stack:** Python standard library, unittest, xml.etree.ElementTree, GitHub Actions/PyInstaller.

---

### Task 1: Dism++ Rule Parser

**Files:**
- Create: `dismpp_rules.py`
- Create: `tests/test_dismpp_rules.py`

- [ ] Write tests for parsing path and wildcard rules from XML.
- [ ] Implement parser with environment expansion, glob support, and safe missing-file behavior.
- [ ] Run `python3 -m unittest tests.test_dismpp_rules`.

### Task 2: Cleaner Integration

**Files:**
- Modify: `cleaner_logic.py`
- Modify: `main.py`
- Modify: `cleaner_ui.py`

- [ ] Add `dismpp_rules` scan category.
- [ ] Add `_scan_dismpp_rules` that delegates to parser and applies `_is_safe_path`.
- [ ] Add UI labels for `Dism++规则`.
- [ ] Run unit tests and py_compile.

### Task 3: Rule Asset and Packaging

**Files:**
- Create: `rules/dismpp/Data.xml`
- Create: `rules/dismpp/LICENSE`
- Modify: `build_exe.py`
- Modify: `.github/workflows/build-windows-exe.yml` if needed

- [ ] Vendor MIT-licensed Dism++ rule metadata.
- [ ] Include `rules` directory in PyInstaller add-data.
- [ ] Run tests and push to GitHub.
- [ ] Confirm GitHub Actions builds artifact.
