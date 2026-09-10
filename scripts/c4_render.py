"""Wrap the Structurizr Mermaid exports in docs/c4/generated into one
GitHub-renderable README.md. Run by `task c4` and by CI after the export.
"""

from pathlib import Path

GENERATED = Path(__file__).resolve().parent.parent / "docs" / "c4" / "generated"
ORDER = [
    "context",
    "containers",
    "k8s-estate",
    "worker-components",
    "deployment",
    "deployment-kind",
]
TITLES = {
    "context": "Level 1 — system context",
    "containers": "Level 2 — the triage brain and its inbound sources",
    "k8s-estate": "Level 2 — the Kubernetes estate: services, Prometheus, Alertmanager route B",
    "worker-components": "Level 3 — inside the triage worker",
    "deployment": "Deployment — where every container runs in `demo` (AWS, Azure)",
    "deployment-kind": "Deployment — where the Kubernetes estate runs (laptop, GitHub Actions)",
}


def main() -> None:
    parts = [
        "# Generated C4 diagrams",
        "",
        "Exported from [`../workspace.dsl`](../workspace.dsl) by `task c4`; do not edit by hand.",
        "",
    ]
    for key in ORDER:
        mmd = GENERATED / f"structurizr-{key}.mmd"
        if not mmd.exists():
            continue
        body = mmd.read_text(encoding="utf-8").strip()
        parts += [f"## {TITLES[key]}", "", "```mermaid", body, "```", ""]
    (GENERATED / "README.md").write_text("\n".join(parts), encoding="utf-8", newline="\n")
    print(f"rendered {GENERATED / 'README.md'}")


if __name__ == "__main__":
    main()
