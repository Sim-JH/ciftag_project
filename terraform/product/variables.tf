variable "desired_count_tasks_fargate_ciftag" {
  description = "Number of instances of the task definition to place and keep running. Defaults to `0`"
  type        = number
  default     = 0
}

variable "run_on" {
  description = "Run default aws"
  type        = string
  default     = "aws"
}

variable "server_type" {
  description = "Set Server Configuration"
  type        = string
  default     = "product"
}

variable "run_type" {
  description = "Crawl Run Type"
  type        = string
  default     = "pinterest"
}

variable "work_id" {
  description = "Crawl Work Ident"
  type        = string
  default     = "0"
}

variable "crypto_key" {
  description = "Crypto Key"
  type        = string
  nullable    = true
  default     = null
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
