provider "aws" {
  region = local.region
}

data "aws_availability_zones" "available" {}

locals {
  region = "ap-northeast-2"
  name   = "ecs-ciftag"
  type   = basename(path.cwd)

  container_name = "ciftag-consumer"
  container_port = 8084

  tags = {
    Name       = local.name
    Example    = local.name
    Repository = "https://github.com/terraform-aws-modules/terraform-aws-ecs"
  }
}

################################################################################
# Cluster
################################################################################

module "ecs_cluster" {
  source = "terraform-aws-modules/ecs/aws//modules/cluster"

  cluster_name     = local.name
  cluster_settings = var.cluster_settings

  # Capacity provider / 용량공급자 100
  fargate_capacity_providers = {
    FARGATE_SPOT = {
      default_capacity_provider_strategy = {
        weight = 100
      }
    }
  }

  tags = local.tags
}

################################################################################
# Service
################################################################################
module "ecs_service_ciftag_product" {
  source = "terraform-aws-modules/ecs/aws//modules/service"

  name        = "ciftag-consumer-${local.type}"
  cluster_arn = var.ciftag_cluster_arn

  cpu                      = 256
  memory                   = 512
  assign_public_ip         = false
  scheduling_strategy      = "DAEMON"
  desired_count            = 0
  autoscaling_min_capacity = 0
  force_new_deployment     = true
  enable_execute_command   = true

  # Container definition(s)
  container_definitions = {
    ciftag-consumer = {
      cpu       = 256
      memory    = 512
      essential = true
      linux_parameters = {
        initProcessEnabled = true
      }

      image = "617204753570.dkr.ecr.ap-northeast-2.amazonaws.com/ciftag-server:latest"

      # 외부 네트워크 접근용 포트
      port_mappings = [
        {
          name          = "ciftag-consumer-${local.type}"
          containerPort = local.container_port
          hostPort      = local.container_port
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          "name" : "RUN_ON",
          "value" : var.run_on
        },
        {
          "name" : "SERVER_TYPE",
          "value" : var.server_type
        },
        {
          "name" : "RUN_TYPE",
          "value" : var.run_type
        }
      ]

      secrets = [
        {
          "name" : "AWS_ACCESS_KEY_ID",
          "valueFrom" : "arn:aws:ssm:ap-northeast-2:617204753570:parameter/secret"
        },
        {
          "name" : "AWS_SECRET_ACCESS_KEY",
          "valueFrom" : "arn:aws:ssm:ap-northeast-2:617204753570:parameter/secret"
        }
      ]

      # Example image used requires access to write to root filesystem
      readonly_root_filesystem = false
    }
  }

  # ecs 클러스터 내의 서비스 간의 통신이 필요할 시 (cloud map)
  # service_connect_configuration = {
  #   namespace = aws_service_discovery_http_namespace.this.arn
  #   service = {
  #     client_alias = {
  #       port     = local.container_port
  #       dns_name = "ciftag-consumer-product"
  #     }
  #     port_name      = "ciftag-consumer-product"
  #     discovery_name = "ciftag-consumer-product"
  #   }
  # }

  subnet_ids = ["subnet-01d7b0f696f7e7aa1"]

  tags = local.tags
}

################################################################################
# Supporting Resources
################################################################################

data "aws_ssm_parameter" "fluentbit" {
  name = "/aws/service/aws-for-fluent-bit/stable"
}

# cloud map 설정
# resource "aws_service_discovery_http_namespace" "this" {
#   name        = local.name
#   description = "CloudMap namespace for ${local.name}"
#   tags        = local.tags
# }

# ecs fargate로 ciftag 수집기 실행
data "aws_ecs_task_execution" "ciftag_fargate_product" {
  count                  = var.init_count_fargate_ciftag
  cluster                = var.ciftag_cluster_arn
  task_definition        = module.ecs_service_ciftag_product.task_definition_arn
  desired_count          = var.desired_count_tasks_fargate_ciftag
  enable_execute_command = true

  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 100
  }

  # fargate subnet 설정 필수 (기본 VPC 사용, 프라이빗 서브넷)
  network_configuration {
    subnets          = ["subnet-01d7b0f696f7e7aa1", "subnet-04978f4993d36dee4", "subnet-0adc0bdd2925bfc5e", "subnet-01c50402b7def20fc"]
    security_groups  = ["sg-081c13aa5c2fc8970"]
    assign_public_ip = false
  }

  tags = local.tags
}

# 대기중인 sqs 갯수 출력
# data "aws_sqs_queues" "ciftag_product" {
#   queue_name_prefix = "ciftag"
# }
# output "ciftag_queue_product" {
#   value = data.aws_sqs_queues.ciftag_product.queue_urls
# }
#
