# ============================================================
# EC2 Auto Start/Stop Scheduler
# ============================================================
# Automatically starts EC2 at office open time (Mon-Fri)
# and stops it at office close time (Mon-Fri).
#
# How it works:
#   EventBridge (cron rule)
#       └── triggers Lambda function
#               └── calls ec2:StartInstances / ec2:StopInstances
#
# Toggle on/off:   set enable_ec2_scheduler = true/false in terraform.tfvars
# Pause without destroy: aws events disable-rule --name <rule-name>
# Resume:          aws events enable-rule --name <rule-name>
# Times:           all crons are in UTC — see variable descriptions
# ============================================================

# ── TOGGLE VARIABLE ─────────────────────────────────────────

variable "enable_ec2_scheduler" {
  description = "Enable automatic EC2 start/stop on a weekday schedule"
  type        = bool
  default     = true
}

# ── TIME VARIABLES (UTC) ────────────────────────────────────
# Buffalo NY timezone offsets:
#   EST (Nov–Mar): UTC-5  →  9 AM EST  = 14:00 UTC | 6 PM EST = 23:00 UTC
#   EDT (Mar–Nov): UTC-4  →  9 AM EDT  = 13:00 UTC | 6 PM EDT = 22:00 UTC
# Cron format: cron(minute hour day-of-month month day-of-week year)
# ? in day-of-month means "any" when day-of-week is specified.

variable "ec2_start_cron_utc" {
  description = "Cron expression (UTC) for EC2 start — default 9 AM EST Mon-Fri"
  type        = string
  default     = "cron(0 14 ? * MON-FRI *)"
}

variable "ec2_stop_cron_utc" {
  description = "Cron expression (UTC) for EC2 stop — default 6 PM EST Mon-Fri"
  type        = string
  default     = "cron(0 23 ? * MON-FRI *)"
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

# ── EVENTBRIDGE RULES (CRON) ─────────────────────────────────

resource "aws_cloudwatch_event_rule" "ec2_start" {
  count               = var.enable_ec2_scheduler ? 1 : 0
  name                = "${var.project_name}-${var.environment}-ec2-start"
  description         = "Start EC2 at office open time (Mon-Fri)"
  schedule_expression = var.ec2_start_cron_utc
  state               = "ENABLED"
  # Note: tags omitted — utility-bot lacks events:TagResource permission
}

resource "aws_cloudwatch_event_rule" "ec2_stop" {
  count               = var.enable_ec2_scheduler ? 1 : 0
  name                = "${var.project_name}-${var.environment}-ec2-stop"
  description         = "Stop EC2 at office close time (Mon-Fri)"
  schedule_expression = var.ec2_stop_cron_utc
  state               = "ENABLED"
  # Note: tags omitted — utility-bot lacks events:TagResource permission
}

# ── CONNECT EVENTBRIDGE → LAMBDA ─────────────────────────────

resource "aws_cloudwatch_event_target" "start_target" {
  count = var.enable_ec2_scheduler ? 1 : 0
  rule  = aws_cloudwatch_event_rule.ec2_start[0].name
  arn   = aws_lambda_function.ec2_start[0].arn
}

resource "aws_cloudwatch_event_target" "stop_target" {
  count = var.enable_ec2_scheduler ? 1 : 0
  rule  = aws_cloudwatch_event_rule.ec2_stop[0].name
  arn   = aws_lambda_function.ec2_stop[0].arn
}

# ── GRANT EVENTBRIDGE PERMISSION TO INVOKE LAMBDA ────────────

resource "aws_lambda_permission" "allow_eventbridge_start" {
  count         = var.enable_ec2_scheduler ? 1 : 0
  statement_id  = "AllowEventBridgeStart"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ec2_start[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ec2_start[0].arn
}

resource "aws_lambda_permission" "allow_eventbridge_stop" {
  count         = var.enable_ec2_scheduler ? 1 : 0
  statement_id  = "AllowEventBridgeStop"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ec2_stop[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ec2_stop[0].arn
}

# ── OUTPUTS ───────────────────────────────────────────────────

output "scheduler_status" {
  value = var.enable_ec2_scheduler ? "ENABLED — Start: ${var.ec2_start_cron_utc} | Stop: ${var.ec2_stop_cron_utc} (UTC)" : "DISABLED"
  description = "EC2 auto start/stop scheduler status"
}
