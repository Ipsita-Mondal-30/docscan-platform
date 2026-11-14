output "cluster_name" { value = module.eks.cluster_name }
output "rds_endpoint" { value = aws_db_instance.mysql.address }
output "ecr_url" { value = aws_ecr_repository.app.repository_url }
