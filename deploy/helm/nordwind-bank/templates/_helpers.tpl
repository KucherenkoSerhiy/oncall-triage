{{/*
Common labels for a per-service object.
*/}}
{{- define "nordwind-bank.labels" -}}
app.kubernetes.io/name: {{ .name }}
app.kubernetes.io/part-of: nordwind-bank
nordwind.dev/c4-container: {{ .name }}
{{- end -}}
