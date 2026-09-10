{{/*
Common labels for a per-service object. `c4Container` is the container's
identifier in docs/c4/workspace.dsl (scripts/c4_drift.py's join key) -
distinct from `name`, the kebab-case k8s object/image name, since a
Structurizr identifier like `openBanking` isn't a legal DNS-1123 name.
*/}}
{{- define "nordwind-bank.labels" -}}
app.kubernetes.io/name: {{ .name }}
app.kubernetes.io/part-of: nordwind-bank
nordwind.dev/c4-container: {{ .c4Container }}
{{- end -}}
