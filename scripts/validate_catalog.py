#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal JSON Schema (draft-07 subset) validator -- standard library only.

Supported keywords: type, required, additionalProperties, enum, pattern,
minItems, uniqueItems, minLength, maxLength, minimum (plus properties/items).

Usage:
    python3 validate_catalog.py <catalog.json> <schema.json>
Exit code 0 on success, 1 on validation failure (path-level errors on stderr).
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

_SIMPLE_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
}


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return isinstance(value, _SIMPLE_TYPES.get(expected, object))


def validate(instance: Any, schema: dict[str, Any], path: str = "$") -> list[dict[str, str]]:
    """Return a list of ``{"path", "message"}`` errors (empty == valid)."""
    errors: list[dict[str, str]] = []
    if not isinstance(schema, dict):
        return errors

    expected = schema.get("type")
    if expected is not None:
        allowed = expected if isinstance(expected, list) else [expected]
        if not any(_type_ok(instance, item) for item in allowed):
            errors.append(
                {
                    "path": path,
                    "message": f"expected type {expected}, got {type(instance).__name__}",
                }
            )
            return errors

    if "enum" in schema and instance not in schema["enum"]:
        errors.append({"path": path, "message": f"value {instance!r} not in enum"})

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(
                {"path": path, "message": f"string shorter than minLength {schema['minLength']}"}
            )
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(
                {"path": path, "message": f"string longer than maxLength {schema['maxLength']}"}
            )
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(
                {"path": path, "message": f"string does not match pattern {schema['pattern']!r}"}
            )

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append({"path": path, "message": f"number below minimum {schema['minimum']}"})

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(
                {"path": path, "message": f"array shorter than minItems {schema['minItems']}"}
            )
        if schema.get("uniqueItems"):
            seen: list[Any] = []
            for index, item in enumerate(instance):
                if item in seen:
                    errors.append(
                        {"path": f"{path}[{index}]", "message": "duplicate item not allowed"}
                    )
                else:
                    seen.append(item)
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                errors.extend(validate(item, item_schema, f"{path}[{index}]"))

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append({"path": f"{path}.{key}", "message": "required property missing"})
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in properties:
                    errors.append(
                        {"path": f"{path}.{key}", "message": "additional property not allowed"}
                    )
        for key, subschema in properties.items():
            if key in instance:
                errors.extend(validate(instance[key], subschema, f"{path}.{key}"))

    return errors


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: validate_catalog.py <catalog.json> <schema.json>", file=sys.stderr)
        return 2
    try:
        with open(argv[0], "r", encoding="utf-8") as handle:
            instance = json.load(handle)
        with open(argv[1], "r", encoding="utf-8") as handle:
            schema = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [{"path": argv[0], "message": str(exc)}]},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    errors = validate(instance, schema)
    if errors:
        print(
            json.dumps({"valid": False, "path": argv[0], "errors": errors},
                       ensure_ascii=False, indent=2),
            file=sys.stderr,
        )
        return 1
    print(json.dumps({"valid": True, "path": argv[0], "count": len(instance.get("projects", []))}
                     if isinstance(instance, dict) else {"valid": True, "path": argv[0]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
