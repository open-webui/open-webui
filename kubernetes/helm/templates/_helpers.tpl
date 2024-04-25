{{- define "open-webui.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end -}}

{{- define "ollama.name" -}}
ollama
{{- end -}}

{{- define "ollama.url" -}}
{{- if .Values.ollama.externalHost }}
{{- printf .Values.ollama.externalHost }}
{{- else }}
{{- printf "http://%s.%s.svc.cluster.local:%d" (include "ollama.name" .) (.Release.Namespace) (.Values.ollama.service.port | int) }}
{{- end }}
{{- end }}

{{- define "chart.name" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "base.labels" -}}
helm.sh/chart: {{ include "chart.name" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "base.selectorLabels" -}}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "open-webui.selectorLabels" -}}
{{ include "base.selectorLabels" . }}
app.kubernetes.io/component: {{ .Chart.Name }}
{{- end }}

{{- define "open-webui.labels" -}}
{{ include "base.labels" . }}
{{ include "open-webui.selectorLabels" . }}
{{- end }}

{{- define "ollama.selectorLabels" -}}
{{ include "base.selectorLabels" . }}
app.kubernetes.io/component: {{ include "ollama.name" . }}
{{- end }}

{{- define "ollama.labels" -}}
{{ include "base.labels" . }}
{{ include "ollama.selectorLabels" . }}
{{- end }}
