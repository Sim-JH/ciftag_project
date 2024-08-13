variable "desired_count_tasks_fargate_ciftag" {
  description = "Number of instances of the task definition to place and keep running. Defaults to `0`"
  type        = number
  default     = 0
}

variable "run_on" {
  description = "Number of instances of the task definition to place and keep running. Defaults to `0`"
  type        = string
  default     = "aws"
}

variable "server_type" {
  description = "Number of instances of the task definition to place and keep running. Defaults to `0`"
  type        = string
  default     = "run"
}

variable "init_count_fargate_ciftag" {
  description = "Number of instances of the task definition to place and keep running. Defaults to `0`"
  type        = number
  default     = 0
}

variable "ciftag_cluster_arn" {
  description = "The ARN of the existing ECS cluster"
  type        = string
  default     = "arn:aws:ecs:ap-northeast-2:617204753570:cluster/ecs-ciftag"
}

# cloudwatch 사용
variable "cluster_settings" {
  description = "Configuration block(s) with cluster settings. For example, this can be used to enable CloudWatch Container Insights for a cluster"
  type        = map(string)
  default = {
    name  = "containerInsights"
    value = "enabled"
  }
}
