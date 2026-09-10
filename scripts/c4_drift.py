"""M8: compares `docs/c4/workspace.dsl` against the `c4_container` Terraform
tags under `infra/**/*.tf` and the `nordwind.dev/c4-container` Helm labels
`helm template deploy/helm/nordwind-bank` renders, and prints a Markdown
drift report.

No cloud calls: Terraform tags are read statically from the `.tf` source
with `python-hcl2` (not `terraform show -json` of a plan or state), and the
Helm set comes from `helm template`'s local rendering. Exits 1 when
Terraform or Helm reference a container the model doesn't declare, or when
a model container tagged `Deployable` appears in neither Terraform nor
Helm - unless `docs/c4/drift-allow.yaml` names it as a deliberate
exception. `--strict` additionally fails the run if the Helm set had to be
skipped (no `helm` on PATH), which `ci.yml`'s `c4` job - where `helm` is
always installed - passes to make a silently-incomplete check impossible.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import hcl2
import yaml
from hcl2.utils import SerializationOptions

REPO_ROOT = Path(__file__).resolve().parent.parent

# strip_string_quotes + explicit_blocks=False collapse python-hcl2 8.x's
# default (quote-preserving, __is_block__-annotated) output back to the
# plain-literal shape this script's dict-walking expects.
_HCL_OPTIONS = SerializationOptions(
    with_comments=False, strip_string_quotes=True, explicit_blocks=False
)

_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
_SYSTEM_LINE_RE = re.compile(rf"^({_IDENT})\s*=\s*softwareSystem\b")
_CONTAINER_LINE_RE = re.compile(rf"^({_IDENT})\s*=\s*container\b")
_QUOTED_RE = re.compile(r'"([^"]*)"')
_LOCAL_TAGS_REF_RE = re.compile(rf"^\$\{{local\.({_IDENT})\.({_IDENT})\}}$")
_C4_CONTAINER_EXPR_RE = re.compile(r'c4_container\s*=\s*"([^"]*)"')
_HELM_LABEL_RE = re.compile(r"nordwind\.dev/c4-container:\s*(\S+)")


@dataclass
class ModelContainer:
    identifier: str
    system: str
    deployable: bool


@dataclass
class TerraformTag:
    container: str
    address: str
    root_default: bool = False


@dataclass
class Violation:
    identifier: str
    reason: str


def parse_model(dsl_text: str) -> dict[str, ModelContainer]:
    """Tolerant line-based parser: `identifier = container "Name" ...`
    inside a `identifier = softwareSystem ... {` block. No `tags "c4:<id>"`
    convention needed - the DSL identifier itself is the join key."""
    model: dict[str, ModelContainer] = {}
    current_system: str | None = None
    for raw_line in dsl_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        system_match = _SYSTEM_LINE_RE.match(line)
        if system_match:
            current_system = system_match.group(1)
            continue
        container_match = _CONTAINER_LINE_RE.match(line)
        if container_match and current_system:
            identifier = container_match.group(1)
            args = _QUOTED_RE.findall(line)
            tags = args[3] if len(args) >= 4 else ""
            deployable = "Deployable" in [t.strip() for t in tags.split(",")]
            model[identifier] = ModelContainer(identifier, current_system, deployable)
    return model


def _extract_c4_container(value: object) -> str | None:
    """`value` is a hcl2-parsed attribute: either an already-resolved dict
    (`tags = { c4_container = "x" }`) or an unresolved expression string
    (`"${merge(local.tags, {c4_container = \"x\"})}"`) hcl2 can't evaluate
    because it involves a function call or a variable reference."""
    if isinstance(value, dict):
        c4 = value.get("c4_container")
        return c4 if isinstance(c4, str) else None
    if isinstance(value, str):
        match = _C4_CONTAINER_EXPR_RE.search(value)
        if match:
            return match.group(1)
    return None


def _local_tag_map(locals_blocks: list[dict]) -> dict[str, str]:
    """Maps `"<local>.<key>"` (e.g. `"tags.payments"`) to the c4_container
    value a resource picks up via `tags = local.tags.payments`."""
    mapping: dict[str, str] = {}
    for block in locals_blocks:
        for top_key, value in block.items():
            if not isinstance(value, dict):
                continue
            for sub_key, sub_value in value.items():
                c4 = _extract_c4_container(sub_value)
                if c4:
                    mapping[f"{top_key}.{sub_key}"] = c4
    return mapping


def _load_hcl(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        try:
            return hcl2.load(f, serialization_options=_HCL_OPTIONS)
        except Exception as exc:
            raise SystemExit(f"c4_drift: failed to parse {path}: {exc}") from exc


def _parse_terraform_root(root: Path) -> list[TerraformTag]:
    resource_blocks: list[dict] = []
    provider_blocks: list[dict] = []
    locals_blocks: list[dict] = []
    for tf_file in sorted(root.glob("*.tf")):
        parsed = _load_hcl(tf_file)
        resource_blocks.extend(parsed.get("resource", []))
        provider_blocks.extend(parsed.get("provider", []))
        locals_blocks.extend(parsed.get("locals", []))

    local_map = _local_tag_map(locals_blocks)
    try:
        rel_root = str(root.relative_to(Path.cwd()))
    except ValueError:
        rel_root = str(root)
    tags: list[TerraformTag] = []

    for provider_block in provider_blocks:
        for provider_attrs in provider_block.values():
            if not isinstance(provider_attrs, dict):
                continue
            for default_tags in provider_attrs.get("default_tags", []):
                c4 = _extract_c4_container(
                    default_tags.get("tags") if isinstance(default_tags, dict) else None
                )
                if c4:
                    tags.append(
                        TerraformTag(
                            container=c4,
                            address=f"{rel_root} (root default_tags - applies to every resource)",
                            root_default=True,
                        )
                    )

    for resource_block in resource_blocks:
        for resource_type, named in resource_block.items():
            if not isinstance(named, dict):
                continue
            for resource_name, attrs in named.items():
                if not isinstance(attrs, dict):
                    continue
                tags_value = attrs.get("tags")
                c4 = None
                if isinstance(tags_value, str):
                    ref_match = _LOCAL_TAGS_REF_RE.match(tags_value)
                    if ref_match:
                        c4 = local_map.get(f"{ref_match.group(1)}.{ref_match.group(2)}")
                    else:
                        c4 = _extract_c4_container(tags_value)
                else:
                    c4 = _extract_c4_container(tags_value)
                if c4:
                    tags.append(
                        TerraformTag(
                            container=c4, address=f"{rel_root}: {resource_type}.{resource_name}"
                        )
                    )
    return tags


def parse_terraform(infra_dir: Path) -> list[TerraformTag]:
    roots = sorted({tf_file.parent for tf_file in infra_dir.rglob("*.tf")})
    tags: list[TerraformTag] = []
    for root in roots:
        tags.extend(_parse_terraform_root(root))
    return tags


def parse_helm(chart_dir: Path) -> tuple[list[str] | None, str | None]:
    """Returns (sorted label values, warning). `helm.enabled=true` so the
    Kafka route-A containers (alerts-bridge, kafka-relay, kafka) render."""
    if not chart_dir.is_dir():
        return None, f"Helm chart not found at {chart_dir} - skipping the Helm set"
    if shutil.which("helm") is None:
        return None, "helm is not on PATH - skipping the Helm set"
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, no untrusted input
        ["helm", "template", str(chart_dir), "--set", "kafka.enabled=true"],  # noqa: S607
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"c4_drift: helm template failed:\n{result.stderr}")
    values = sorted(set(_HELM_LABEL_RE.findall(result.stdout)))
    return values, None


def load_allow_list(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    entries = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return {entry["container"]: entry["reason"] for entry in entries}


def _render_table(
    rows: list[tuple[str, str, bool, bool, str, str | None]], helm_ran: bool
) -> list[str]:
    lines = ["| Container | In model | In Terraform | In Helm | Where |", "|---|---|---|---|---|"]
    for identifier, in_model, in_tf, in_helm, where, allow_reason in rows:
        helm_col = "skipped" if not helm_ran else ("yes" if in_helm else "no")
        cell_where = where or "-"
        if allow_reason:
            cell_where += f" (allow-listed: {allow_reason})"
        tf_col = "yes" if in_tf else "no"
        lines.append(f"| {identifier} | {in_model} | {tf_col} | {helm_col} | {cell_where} |")
    lines.append("")
    return lines


def build_report(
    model: dict[str, ModelContainer],
    tf_tags: list[TerraformTag],
    helm_values: list[str] | None,
    allow_list: dict[str, str],
) -> tuple[str, list[Violation]]:
    helm_ran = helm_values is not None
    helm_set = set(helm_values or [])
    tf_by_container: dict[str, list[str]] = defaultdict(list)
    for tag in tf_tags:
        tf_by_container[tag.container].append(tag.address)

    systems_order: list[str] = []
    by_system: dict[str, list[str]] = defaultdict(list)
    for identifier, container in model.items():
        if container.system not in systems_order:
            systems_order.append(container.system)
        by_system[container.system].append(identifier)

    violations: list[Violation] = []
    lines = ["# C4 drift report", ""]

    for system in systems_order:
        rows = []
        for identifier in sorted(by_system[system]):
            container = model[identifier]
            in_tf = identifier in tf_by_container
            in_helm = identifier in helm_set
            allow_reason = allow_list.get(identifier)
            if container.deployable and not in_tf and not in_helm and not allow_reason:
                violations.append(
                    Violation(identifier, "deployable but missing from Terraform and Helm")
                )
            where = "; ".join(sorted(tf_by_container.get(identifier, [])))
            if in_helm:
                where = "; ".join(filter(None, [where, "helm: nordwind-bank chart"]))
            rows.append((identifier, "yes", in_tf, in_helm, where, allow_reason))
        lines.append(f"## {system}")
        lines.append("")
        lines.extend(_render_table(rows, helm_ran))

    extra = sorted((set(tf_by_container) | helm_set) - set(model))
    if extra:
        rows = []
        for identifier in extra:
            in_tf = identifier in tf_by_container
            in_helm = identifier in helm_set
            allow_reason = allow_list.get(identifier)
            if not allow_reason:
                violations.append(
                    Violation(identifier, "referenced by Terraform or Helm but not in the model")
                )
            where = "; ".join(sorted(tf_by_container.get(identifier, [])))
            if in_helm:
                where = "; ".join(filter(None, [where, "helm: nordwind-bank chart"]))
            rows.append((identifier, "no", in_tf, in_helm, where, allow_reason))
        lines.append("## Not declared in the model")
        lines.append("")
        lines.extend(_render_table(rows, helm_ran))

    return "\n".join(lines).rstrip() + "\n", violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=REPO_ROOT, help="repository root (tests point elsewhere)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="also fail if the Helm set had to be skipped, instead of just warning",
    )
    args = parser.parse_args(argv)
    root: Path = args.repo_root

    model = parse_model((root / "docs" / "c4" / "workspace.dsl").read_text(encoding="utf-8"))
    tf_tags = parse_terraform(root / "infra")
    helm_values, helm_warning = parse_helm(root / "deploy" / "helm" / "nordwind-bank")
    allow_list = load_allow_list(root / "docs" / "c4" / "drift-allow.yaml")

    report, violations = build_report(model, tf_tags, helm_values, allow_list)
    print(report)

    exit_code = 0
    if violations:
        exit_code = 1
        for violation in violations:
            print(f"drift: {violation.identifier}: {violation.reason}", file=sys.stderr)
    if helm_warning:
        print(f"WARNING: {helm_warning}", file=sys.stderr)
        if args.strict:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
