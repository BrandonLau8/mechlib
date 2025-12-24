# SNS Topic for CloudWatch Alerts
resource "aws_sns_topic" "alerts" {
  name = "mechlib-alerts-${var.environment}"

  tags = {
    Name = "mechlib-alerts-${var.environment}"
  }
}

# SNS Email Subscription (you'll need to confirm via email after terraform apply)
resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Purpose: Central location for application and system logs
# Retention: Logs are kept for 30 days, then automatically deleted (cost optimization)
# Use case: Your EC2 instance can send application logs, PostgreSQL logs, system logs, etc. here for centralized viewing and searching
resource "aws_cloudwatch_log_group" "mechlib" {
  name              = "/mechlib/${var.environment}"
  retention_in_days = 30
}

# Monitors disk usage and alerts when space is running low:
resource "aws_cloudwatch_metric_alarm" "disk_space" {
  alarm_name          = "mechlib-disk-full-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1 # Alarms immediately on first breach (no grace period)
  metric_name         = "DiskSpaceUsed" # Tracks disk space consumption
  namespace           = "AWS/EC2" #
  period              = 300 # Checks every 5 minutes (300 seconds)
  statistic           = "Average" # Uses average disk usage over the 5-minute window
  threshold           = 80 # Triggers when disk usage exceeds 80%
  alarm_actions       = [aws_sns_topic.alerts.arn] # Sends notification to SNS topic when triggered
}


 # The Logic:
 #  1. Every 5 minutes, CloudWatch collects the DiskSpaceUsed metric
 #  2. Calculates the average disk usage over that 5-minute window
 #  3. If average > 80% then evaluation passes (1/1 needed)
 #  4. Alarm state changes to ALARM → triggers SNS notification
