# ============================================================
# EC2 Auto Start/Stop Scheduler
# ============================================================
# Automatically starts EC2 at office open time (Mon-Fri)
# and stops it at office close time (Mon-Fri).
#
# How it works:
#   EventBridge Scheduler (timezone-aware)
#       └── triggers Lambda function
#               └── calls ec2:StartInstances / ec2:StopInstances
#
# DST handled automatically — uses America/New_York timezone
# so clocks never need manual adjustment for EST/EDT changes.
#
# Toggle on/off:   set enable_ec2_scheduler = true/false in terraform.tfvars
# Pause:           set state = "DISABLED" in aws_scheduler_schedule and apply
# Times:           set in local time (America/New_York) — no UTC math needed
# ============================================================

# ── TOGGLE VARIABLE ─────────────────────────────────────────

variable "enable_ec2_scheduler" {
  description = "Enable automatic EC2 start/stop on a weekday schedule"
  type        = bool
  default     = true
}

# ── TIME VARIABLES (LOCAL TIME — America/New_York) ──────────
# These are in local New York time — DST is handled automatically.
# Format: cron(minute hour day-of-month month day-of-week year)
# Example: cron(0 9 ? * MON-FRI *) = 9:00 AM every weekday

variable "ec2_start_cron_local" {
  description = "Cron (America/New_York) for EC2 start — default 9 AM Mon-Fri"
  type        = string
  default     = "cron(0 9 ? * MON-FRI *)"
}

variable "ec2_stop_cron_local" {
  description = "Cron (America/New_York) for EC2 stop — default 6 PM Mon-Fri"
  type        = string
  default     = "cron(0 18 ? * MON-FRI *)"
}

# ── IAM ROLE FOR LAMBDA ─────────────────────────────────────
# Lambda needs permission to be invoked, and to start/stop EC2.

resource "aws_iam_role" "scheduler_lambda_role" {
  count = var.enable_ec2_scheduler ? 1 : 0
  name  = "${var.project_name}-${var.environment}-scheduler-lambda-role"

  # Allow Lambda service to assume this role.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Allow Lambda to write logs to CloudWatch (for debugging).
resource "aws_iam_role_policy_attachment" "lambda_basic_logs" {
  count      = var.enable_ec2_scheduler ? 1 : 0
  role       = aws_iam_role.scheduler_lambda_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Allow Lambda to start and stop this specific EC2 instance only.
resource "aws_iam_role_policy" "lambda_ec2_startstop" {
  count = var.enable_ec2_scheduler ? 1 : 0
  name  = "${var.project_name}-${var.environment}-lambda-ec2-startstop"
  role  = aws_iam_role.scheduler_lambda_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:DescribeInstances"
      ]
      # Scoped to this specific EC2 instance only.
      Resource = [aws_instance.app.arn]
    }]
  })
}

# ── LAMBDA FUNCTION: START EC2 ───────────────────────────────

# Zip the inline Python code so Lambda can run it.
data "archive_file" "start_lambda_zip" {
  count       = var.enable_ec2_scheduler ? 1 : 0
  type        = "zip"
  output_path = "${path.module}/lambda_start.zip"

  source {
    content  = <<-PYTHON
import boto3, os

def handler(event, context):
    ec2 = boto3.client("ec2", region_name=os.environ["AWS_REGION_NAME"])
    instance_id = os.environ["INSTANCE_ID"]
    ec2.start_instances(InstanceIds=[instance_id])
    print(f"Started EC2 instance: {instance_id}")
    return {"status": "started", "instance_id": instance_id}
PYTHON
    filename = "lambda_function.py"
  }
}

resource "aws_lambda_function" "ec2_start" {
  count            = var.enable_ec2_scheduler ? 1 : 0
  function_name    = "${var.project_name}-${var.environment}-ec2-start"
  role             = aws_iam_role.scheduler_lambda_role[0].arn
  handler          = "lambda_function.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.start_lambda_zip[0].output_path
  source_code_hash = data.archive_file.start_lambda_zip[0].output_base64sha256
  timeout          = 30

  environment {
    variables = {
      INSTANCE_ID     = aws_instance.app.id
      AWS_REGION_NAME = var.aws_region
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "EC2 scheduled start"
  }
}

# ── LAMBDA FUNCTION: STOP EC2 ────────────────────────────────

data "archive_file" "stop_lambda_zip" {
  count       = var.enable_ec2_scheduler ? 1 : 0
  type        = "zip"
  output_path = "${path.module}/lambda_stop.zip"

  source {
    content  = <<-PYTHON
import boto3, os

def handler(event, context):
    ec2 = boto3.client("ec2", region_name=os.environ["AWS_REGION_NAME"])
    instance_id = os.environ["INSTANCE_ID"]
    ec2.stop_instances(InstanceIds=[instance_id])
    print(f"Stopped EC2 instance: {instance_id}")
    return {"status": "stopped", "instance_id": instance_id}
PYTHON
    filename = "lambda_function.py"
  }
}

resource "aws_lambda_function" "ec2_stop" {
  count            = var.enable_ec2_scheduler ? 1 : 0
  function_name    = "${var.project_name}-${var.environment}-ec2-stop"
  role             = aws_iam_role.scheduler_lambda_role[0].arn
  handler          = "lambda_function.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.stop_lambda_zip[0].output_path
  source_code_hash = data.archive_file.stop_lambda_zip[0].output_base64sha256
  timeout          = 30

  environment {
    variables = {
      INSTANCE_ID     = aws_instance.app.id
      AWS_REGION_NAME = var.aws_region
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "EC2 scheduled stop"
  }
}

# ── IAM ROLE FOR EVENTBRIDGE SCHEDULER → LAMBDA ──────────────
# EventBridge Scheduler needs its own role to invoke Lambda.
# (Different from the Lambda execution role above.)

resource "aws_iam_role" "scheduler_invoke_role" {
  count = var.enable_ec2_scheduler ? 1 : 0
  name  = "${var.project_name}-${var.environment}-scheduler-invoke-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_iam_role_policy" "scheduler_invoke_lambda" {
  count = var.enable_ec2_scheduler ? 1 : 0
  name  = "${var.project_name}-${var.environment}-scheduler-invoke-lambda"
  role  = aws_iam_role.scheduler_invoke_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["lambda:InvokeFunction"]
      Resource = [
        aws_lambda_function.ec2_start[0].arn,
        aws_lambda_function.ec2_stop[0].arn
      ]
    }]
  })
}

# ── EVENTBRIDGE SCHEDULER (TIMEZONE-AWARE) ───────────────────
# Uses America/New_York timezone — handles EST/EDT automatically.
# No UTC math needed. No manual adjustment for DST ever.

resource "aws_scheduler_schedule" "ec2_start" {
  count       = var.enable_ec2_scheduler ? 1 : 0
  name        = "${var.project_name}-${var.environment}-ec2-start"
  description = "Start EC2 at 9 AM New York time, Mon-Fri (DST-aware)"

  schedule_expression          = var.ec2_start_cron_local
  schedule_expression_timezone = "America/New_York"

  flexible_time_window {
    mode = "OFF"  # Fire exactly on time, no flexibility window
  }

  target {
    arn      = aws_lambda_function.ec2_start[0].arn
    role_arn = aws_iam_role.scheduler_invoke_role[0].arn
  }
}

resource "aws_scheduler_schedule" "ec2_stop" {
  count       = var.enable_ec2_scheduler ? 1 : 0
  name        = "${var.project_name}-${var.environment}-ec2-stop"
  description = "Stop EC2 at 6 PM New York time, Mon-Fri (DST-aware)"

  schedule_expression          = var.ec2_stop_cron_local
  schedule_expression_timezone = "America/New_York"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.ec2_stop[0].arn
    role_arn = aws_iam_role.scheduler_invoke_role[0].arn
  }
}

# ── OUTPUTS ───────────────────────────────────────────────────

output "scheduler_status" {
  value       = var.enable_ec2_scheduler ? "ENABLED — Start: 9:00 AM Mon-Fri | Stop: 6:00 PM Mon-Fri (America/New_York — DST auto-handled)" : "DISABLED"
  description = "EC2 auto start/stop scheduler status"
}
