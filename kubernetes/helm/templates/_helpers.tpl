{{- define "open-webui.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end -}}

{{- define "ollama.name" -}}
ollama
{{- end -}}
