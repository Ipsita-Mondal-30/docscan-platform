# Request path: client to OCR result

1. **DNS**: `docscan.localtest.me` resolves to 127.0.0.1 (kind maps host ports 80/443 to the ingress node).
2. **Ingress controller (nginx)** in `ingress-nginx`: matches Host + path and proxies to the `docscan-api` Service.
3. **Service (ClusterIP)**: kube-proxy (iptables/IPVS) DNATs the virtual IP to one ready API pod. Pods that fail `/readyz` are removed from the endpoints.
4. **API pod** writes the file to the shared volume, inserts a row in MySQL (`mysql:3306`), pushes the job ID to Redis (`redis:6379`), and returns `202`.
5. **Worker pod** blocks on `BLPOP`, reads the file, runs OCR, and updates the row. The client polls `GET /v1/jobs/{id}`.

## Network policies
Default deny in the namespace. Allowed: ingress-nginx and monitoring to the API (8000), monitoring to workers (9100), API and workers to MySQL/Redis/DNS. Nothing else. To debug a blocked flow: `kubectl -n docscan exec deploy/docscan-api -- python -c "import socket; socket.create_connection(('mysql',3306),3)"`.
