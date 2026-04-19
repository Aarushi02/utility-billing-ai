# ============================================================
# SSM Parameter Store — App Secrets
# ============================================================
# All app secrets are stored here as SecureString (encrypted).
# EC2 IAM role has read access — no .env file needs to be
# manually copied to the server ever again.
#
# Developers: add values to terraform.tfvars under app_secrets
# and run terraform apply to push updated secrets to SSM.
#
# On EC2: scripts/fetch_secrets.sh pulls all params and
# writes the .env file automatically before docker compose up.
# ============================================================

variable "app_secrets" {
  description = "App secrets stored as SSM SecureString parameters"
  type        = map(string)
  default     = {}
}

resource "aws_ssm_parameter" "app_secret" {
  # config.py builds DB_URL at runtime from DB_HOST/USER/PASSWORD/PORT/NAME — no DB_URL param needed.
  for_each = var.app_secrets

  name        = "/${var.project_name}/${var.environment}/${each.key}"
  type        = "SecureString"
  value       = each.value
  overwrite   = true

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Allow EC2 to read all parameters under this project/env path.
resource "aws_iam_role_policy" "ec2_ssm_parameters" {
  name = "${var.project_name}-${var.environment}-ssm-params"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ]
      Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/${var.project_name}/${var.environment}/*"
    },
    {
      Effect   = "Allow"
      Action   = ["kms:Decrypt"]
      Resource = "*"
    }]
  })
}

output "ssm_parameter_path" {
  value       = "/${var.project_name}/${var.environment}/"
  description = "Base path for all SSM parameters — view in AWS Console → Systems Manager → Parameter Store"
}
