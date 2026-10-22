"""Compare a hosted feature service's live schema with an expected definition (schema drift)."""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Issue:
    severity: str   # "error" or "warning"
    layer: str
    message: str


def describe_layers(item) -> dict[str, dict]:
    """Plain-dict description of each layer: geometry type, field types and time field."""
    layers = {}
    for layer in item.layers:
        p = layer.properties
        layers[p["name"]] = {
            "geometryType": p.get("geometryType"),
            "fields": {f["name"]: f["type"] for f in p.get("fields") or []},
            "timeField": (p.get("timeInfo") or {}).get("startTimeField"),
        }
    return layers


def compare(expected: dict[str, dict], actual: dict[str, dict]) -> list[Issue]:
    issues = []
    for name, exp in expected.items():
        if name not in actual:
            issues.append(Issue("error", name, "layer is missing"))
            continue
        act = actual[name]

        if exp.get("geometryType") != act.get("geometryType"):
            issues.append(Issue("error", name, f"geometry type is {act.get('geometryType')}, "
                                               f"expected {exp.get('geometryType')}"))

        for field, ftype in exp["fields"].items():
            if field not in act["fields"]:
                issues.append(Issue("error", name, f"field '{field}' is missing"))
            elif act["fields"][field] != ftype:
                issues.append(Issue("error", name, f"field '{field}' is {act['fields'][field]}, "
                                                   f"expected {ftype}"))
        for field in act["fields"].keys() - exp["fields"].keys():
            issues.append(Issue("warning", name, f"unexpected field '{field}'"))

        if exp.get("timeField") and exp["timeField"] != act.get("timeField"):
            issues.append(Issue("error", name, f"time field is {act.get('timeField')}, "
                                               f"expected {exp['timeField']}"))

    for name in actual.keys() - expected.keys():
        issues.append(Issue("warning", name, "unexpected layer"))
    return issues


def write_schema(service: str, layers: dict, path: Path) -> None:
    path.write_text(json.dumps({"service": service, "layers": layers}, indent=2, sort_keys=True))


def read_schema(path: Path) -> dict:
    return json.loads(path.read_text())