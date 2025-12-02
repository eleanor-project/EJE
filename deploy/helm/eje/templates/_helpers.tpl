{{- define "eje.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "eje.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "eje.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "eje.labels" -}}
helm.sh/chart: {{ include "eje.chart" . }}
app.kubernetes.io/name: {{ include "eje.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . | indent 0 }}
{{- end }}
{{- end -}}

{{- define "eje.selectorLabels" -}}
app.kubernetes.io/name: {{ include "eje.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "eje.postgresql.host" -}}
{{- if .Values.postgresql.enabled -}}
{{- printf "%s-postgresql" (include "eje.fullname" .) -}}
{{- else -}}
{{- .Values.postgresql.external.host | default "" -}}
{{- end -}}
{{- end -}}

{{- define "eje.postgresql.port" -}}
{{- if .Values.postgresql.enabled -}}
5432
{{- else -}}
{{- .Values.postgresql.external.port | default 5432 -}}
{{- end -}}
{{- end -}}

{{- define "eje.postgresql.user" -}}
{{- if .Values.postgresql.enabled -}}
{{- .Values.postgresql.auth.username -}}
{{- else -}}
{{- .Values.postgresql.external.user -}}
{{- end -}}
{{- end -}}

{{- define "eje.postgresql.database" -}}
{{- if .Values.postgresql.enabled -}}
{{- .Values.postgresql.auth.database -}}
{{- else -}}
{{- .Values.postgresql.external.database -}}
{{- end -}}
{{- end -}}

{{- define "eje.postgresql.secretName" -}}
{{- if .Values.postgresql.enabled -}}
{{- printf "%s-postgresql" (include "eje.fullname" .) -}}
{{- else -}}
{{- .Values.postgresql.external.passwordSecretName -}}
{{- end -}}
{{- end -}}

{{- define "eje.postgresql.secretKey" -}}
{{- if .Values.postgresql.enabled -}}
postgres-password
{{- else -}}
{{- .Values.postgresql.external.passwordSecretKey -}}
{{- end -}}
{{- end -}}

{{- define "eje.redis.host" -}}
{{- if .Values.redis.enabled -}}
{{- printf "%s-redis-master" (include "eje.fullname" .) -}}
{{- else -}}
{{- .Values.redis.external.host | default "" -}}
{{- end -}}
{{- end -}}

{{- define "eje.redis.port" -}}
{{- if .Values.redis.enabled -}}
6379
{{- else -}}
{{- .Values.redis.external.port | default 6379 -}}
{{- end -}}
{{- end -}}

{{- define "eje.redis.secretName" -}}
{{- if .Values.redis.enabled -}}
{{- printf "%s-redis" (include "eje.fullname" .) -}}
{{- else -}}
{{- .Values.redis.external.passwordSecretName -}}
{{- end -}}
{{- end -}}

{{- define "eje.redis.secretKey" -}}
{{- if .Values.redis.enabled -}}
redis-password
{{- else -}}
{{- .Values.redis.external.passwordSecretKey -}}
{{- end -}}
{{- end -}}
