#!/usr/bin/env python3
"""Cut a large OpenAPI 3 spec down to the few operations a Dify Custom Tool needs.

    python tools/openapi_slim.py tools/grafana-incident.slim.yaml

The config file (YAML) says which spec to read, which operations to keep, and
how to rewrite them for an LLM:

    source: grafana-openapi3.json        # path or https:// URL, JSON or YAML
    server: https://grafana.internal/api # replaces servers[]
    output: dist/grafana-incident.yaml
    drop_responses: true                 # keep only a stub "200" response
    operations:
      - path: /annotations
        method: get
        operation_id: get_annotations    # optional rename
        summary: ...                     # optional override (what the agent sees)
        keep_params: [from, to, tags, limit]  # optional, drop other params
    extra_paths: {...}                   # optional, hand-written paths merged in

Only components reachable from the kept operations are copied, so the result
stays small. Requires PyYAML.
"""

import copy
import json
import re
import sys
import urllib.request
from pathlib import Path

import yaml

METHODS = {"get", "put", "post", "delete", "patch", "head", "options"}


def load_any(source: str, base: Path):
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source) as resp:  # noqa: S310 - user-supplied spec URL
            text = resp.read().decode("utf-8")
    else:
        text = (base / source).read_text(encoding="utf-8")
    return json.loads(text) if text.lstrip().startswith("{") else yaml.safe_load(text)


def refs_in(node):
    """Yield every $ref string inside node."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield value
            else:
                yield from refs_in(value)
    elif isinstance(node, list):
        for item in node:
            yield from refs_in(item)


def collect_components(spec, roots):
    """Return {section: {name: obj}} for components reachable from roots."""
    components = spec.get("components", {})
    keep = {}
    pending = list(refs_in(roots))
    seen = set()
    while pending:
        ref = pending.pop()
        if ref in seen or not ref.startswith("#/components/"):
            continue
        seen.add(ref)
        _, _, section, name = ref.split("/", 3)
        obj = components.get(section, {}).get(name)
        if obj is None:
            print(f"warning: unresolved {ref}", file=sys.stderr)
            continue
        keep.setdefault(section, {})[name] = obj
        pending.extend(refs_in(obj))
    return keep


def default_operation_id(method, path):
    words = re.sub(r"[{}]", "", path).strip("/").replace("/", "_").replace("-", "_")
    return f"{method}_{words}" or method


def slim(config, base: Path):
    spec = load_any(config["source"], base)
    if not str(spec.get("openapi", "")).startswith("3"):
        sys.exit("source must be OpenAPI 3.x (convert Swagger 2.0 first, e.g. Grafana public/openapi3.json)")

    paths = {}
    for item in config["operations"]:
        path, method = item["path"], item["method"].lower()
        if method not in METHODS:
            sys.exit(f"bad method {method} for {path}")
        source_item = spec["paths"].get(path)
        if not source_item or method not in source_item:
            sys.exit(f"{method.upper()} {path} not found in source spec")
        op = copy.deepcopy(source_item[method])
        # Path-level parameters apply to every method; fold them into the operation.
        params = copy.deepcopy(source_item.get("parameters", [])) + op.get("parameters", [])
        if "keep_params" in item:
            allowed = set(item["keep_params"])
            params = [p for p in params if "$ref" in p or p.get("name") in allowed or p.get("in") == "path"]
        if params:
            op["parameters"] = params
        op["operationId"] = item.get("operation_id") or op.get("operationId") or default_operation_id(method, path)
        for key in ("summary", "description"):
            if key in item:
                op[key] = item[key]
        if config.get("drop_responses"):
            op["responses"] = {"200": {"description": "OK"}}
        for noisy in ("tags", "security", "x-codegen-request-body-name"):
            op.pop(noisy, None)
        paths.setdefault(path, {})[method] = op

    for path, methods in (config.get("extra_paths") or {}).items():
        paths.setdefault(path, {}).update(methods)

    out = {
        "openapi": spec["openapi"],
        "info": {
            "title": config.get("title", spec.get("info", {}).get("title", "api")),
            "version": str(config.get("version", spec.get("info", {}).get("version", "1"))),
        },
        "servers": [{"url": config["server"]}],
        "paths": paths,
    }
    components = collect_components(spec, paths)
    if components:
        out["components"] = components
    return out


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    config_path = Path(sys.argv[1]).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    out = slim(config, config_path.parent)

    target = config_path.parent / config["output"]
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix == ".json":
        target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        target.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")

    ops = sum(len(m) for m in out["paths"].values())
    schemas = sum(len(v) for v in out.get("components", {}).values())
    print(f"{target}  {ops} operations, {schemas} components, {target.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
