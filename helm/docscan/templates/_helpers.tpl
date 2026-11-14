{{- define "docscan.image" -}}{{ .Values.image.repository }}:{{ .Values.image.tag }}{{- end -}}
{{- define "docscan.env" -}}
- {name: DOCSCAN_REDIS_URL, value: {{ .Values.config.redisUrl | quote }}}
- name: DOCSCAN_MYSQL_PASSWORD
  valueFrom: {secretKeyRef: {name: docscan, key: mysql-password}}
- name: DOCSCAN_DATABASE_URL
  value: mysql+pymysql://{{ .Values.config.mysqlUser }}:$(DOCSCAN_MYSQL_PASSWORD)@{{ .Values.config.mysqlHost }}:3306/{{ .Values.config.mysqlDatabase }}
{{- end -}}
{{- define "docscan.secctx" -}}
runAsNonRoot: true
runAsUser: 10001
allowPrivilegeEscalation: false
capabilities: {drop: ["ALL"]}
{{- end -}}
