# The triage-worker image repository lives in its own root so it can be
# created before infra/aws exists to reference it - see infra/README.md
# for the ecr -> image -> plan -> apply ordering this avoids a chicken-egg
# race on a fresh account (infra/aws's Lambda needs an image URI to exist
# in its very first apply).

resource "aws_ecr_repository" "triage_worker" {
  name                 = "${local.name_prefix}-triage-worker"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    c4_container = "worker"
  }
}

resource "aws_ecr_lifecycle_policy" "triage_worker" {
  repository = aws_ecr_repository.triage_worker.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep the last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
