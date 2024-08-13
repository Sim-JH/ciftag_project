# 다이나모 DB에 테이블을 생성
# resource "aws_dynamodb_table" "terraform_locks" {
#   name         = "terraform-up-and-running-locks"
#   billing_mode = "PAY_PER_REQUEST"
#   hash_key     = "LockID"
#
#   attribute {
#     name = "LockID"
#     type = "S"
#   }
# }

terraform {
  backend "s3" {
    # ciftag 수집 bucket에 포함
    bucket = "ciftag-bucket"
    key    = "global/ciftag/terraform.tfstate"
    region = "ap-northeast-2"

    # 단일 실행 환경이라 일단 다이나모 db 설정 x
    # dynamodb_table = "terraform-up-and-running-locks"
    encrypt = true
  }
}
