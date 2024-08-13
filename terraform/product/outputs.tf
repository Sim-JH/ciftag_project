# ################################################################################
# # Service
# ################################################################################

output "service_name" {
  description = "Name of the service"
  value       = module.ecs_service_ciftag_product.name
}

output "service_task_definition_arn" {
  description = "Full ARN of the Task Definition (including both `family` and `revision`)"
  value       = module.ecs_service_ciftag_product.task_definition_arn
}
