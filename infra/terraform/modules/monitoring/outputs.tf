output "sns_alarm_topic_arn"    { value = aws_sns_topic.alarms.arn }
output "cloudwatch_dashboard"   { value = aws_cloudwatch_dashboard.mlops.dashboard_name }
output "cloudtrail_bucket"      { value = aws_s3_bucket.cloudtrail.bucket }
output "cloudtrail_log_group"   { value = aws_cloudwatch_log_group.cloudtrail.name }
