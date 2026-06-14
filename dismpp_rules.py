#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dism++ Data.xml rule scanner.

Only conservative file and directory rules are supported. Dynamic Dism++
functions, registry actions, custom actions, and command-like rules are ignored.
"""

import glob
import fnmatch
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


_ENV_PATTERN = re.compile(r"%([^%]+)%")


def get_resource_path(*parts):
    """Return a path that works both from source and a PyInstaller bundle."""
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return Path(base_dir).joinpath(*parts)


def get_default_rules_path():
    """Return the bundled Dism++ Data.xml path."""
    return get_resource_path("rules", "dismpp", "Data.xml")


def _clean_label(value):
    if not value:
        return ""
    return value.lstrip("#").strip()


class DismRuleScanner:
    """Scan file-system cleanup candidates from Dism++ Data.xml General rules."""

    def __init__(self, rules_path=None, env=None):
        self.rules_path = Path(rules_path) if rules_path else get_default_rules_path()
        self.env = dict(os.environ if env is None else env)

    def scan(self):
        """Return normalized cleanup candidates from supported Dism++ rules."""
        if not self.rules_path.exists():
            return []

        tree = ET.parse(self.rules_path)
        results = []
        seen = set()

        for item in tree.findall(".//Item"):
            rule_name = _clean_label(item.attrib.get("Name", "Dism++规则"))
            group = _clean_label(self._child_text(item, "Group"))

            for general in item.findall(".//General"):
                for path in self._scan_general(general):
                    normalized = os.path.normcase(os.path.abspath(path))
                    if normalized in seen:
                        continue
                    seen.add(normalized)
                    results.append(
                        {
                            "path": path,
                            "size": self._path_size(path),
                            "type": "dismpp_rules",
                            "rule_name": rule_name,
                            "group": group,
                        }
                    )

        return results

    def _scan_general(self, general):
        root_path = general.attrib.get("RootPath", "").strip()
        if not root_path:
            return []

        root_path = self._expand_path(root_path)
        if not root_path:
            return []

        queries = [self._normalize_query(q.text) for q in general.findall("Query") if q.text]
        excludes = [self._normalize_query(e.text) for e in general.findall("Excluded") if e.text]
        excludes = [pattern for pattern in excludes if pattern and not self._is_dynamic_expression(pattern)]

        if not queries:
            return [root_path] if os.path.exists(root_path) and not self._is_excluded(root_path, root_path, excludes) else []

        matches = []
        for query in queries:
            if not query or self._is_dynamic_expression(query):
                continue

            pattern = os.path.join(root_path, query)
            for match in glob.glob(pattern, recursive=True):
                if os.path.exists(match) and not self._is_excluded(root_path, match, excludes):
                    matches.append(match)

        return matches

    def _expand_path(self, path):
        if self._is_dynamic_expression(path):
            return None

        aliases = {
            "SystemDrive": self.env.get("SystemDrive", "C:"),
            "SystemRoot": self.env.get("SystemRoot", os.path.join(self.env.get("SystemDrive", "C:"), "Windows")),
            "WinDir": self.env.get("WinDir", os.path.join(self.env.get("SystemDrive", "C:"), "Windows")),
        }
        aliases["System"] = self.env.get("System", os.path.join(aliases["SystemRoot"], "System32"))

        def replace_env(match):
            name = match.group(1)
            return self.env.get(name, self.env.get(name.upper(), aliases.get(name, match.group(0))))

        expanded = _ENV_PATTERN.sub(replace_env, path)
        if "%" in expanded or self._is_dynamic_expression(expanded):
            return None
        if os.sep != "\\":
            expanded = expanded.replace("\\", os.sep)
        return os.path.normpath(expanded)

    def _is_excluded(self, root_path, path, exclude_patterns):
        if not exclude_patterns:
            return False

        rel_path = os.path.relpath(path, root_path)
        name = os.path.basename(path)

        for pattern in exclude_patterns:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return True
        return False

    @staticmethod
    def _normalize_query(value):
        value = value.strip()
        if value == "{*}":
            return "*"
        return value

    @staticmethod
    def _is_dynamic_expression(value):
        return value.strip().startswith("?") or "?Get" in value

    @staticmethod
    def _path_size(path):
        try:
            if os.path.isfile(path):
                return os.path.getsize(path)
            if os.path.isdir(path):
                total = 0
                for root, _, files in os.walk(path):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        try:
                            if os.path.isfile(file_path):
                                total += os.path.getsize(file_path)
                        except (PermissionError, FileNotFoundError):
                            pass
                return total
        except (PermissionError, FileNotFoundError):
            return 0
        return 0

    @staticmethod
    def _child_text(element, tag):
        child = element.find(tag)
        return child.text if child is not None else ""
