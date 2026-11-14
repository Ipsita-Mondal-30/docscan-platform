# Runbook

## QueueBacklog (queue depth > 50 for 5m)
1. `kubectl -n docscan get hpa docscan-worker`: is it at maxReplicas? If yes, raise `worker.maxReplicas` in `helm/docscan/values.yaml` and merge (Argo CD syncs it).
2. `kubectl -n docscan logs deploy/docscan-worker --tail=100`: look for repeating exceptions or one very slow document.
3. Check Redis: `kubectl -n docscan exec deploy/redis -- redis-cli llen docscan:jobs`.

## HighJobFailureRate
1. Query MySQL: `SELECT error, COUNT(*) FROM jobs WHERE status='failed' AND created_at > NOW() - INTERVAL 1 HOUR GROUP BY error;`
2. "cannot decode image" spikes usually mean a bad client upload, not an outage.
3. Failures across all error types: check the last deploy in Argo CD and roll back by reverting the image-tag commit in git.

## Rollback (GitOps)
`git revert <ci deploy commit>` and push. Argo CD reconciles. Never `kubectl edit` live resources: `selfHeal` will undo it.

## Restore MySQL
Backups are written by the `mysql-backup` CronJob (demo: emptyDir; production: mount an S3-backed or EBS volume, or rely on RDS automated backups with 7-day retention).
