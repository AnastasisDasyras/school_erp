#!/usr/bin/env bash
# Runs automatically when the LocalStack container is ready (mounted into
# /etc/localstack/init/ready.d/). Creates the messaging infra used from Phase 4 onward.
set -euo pipefail

TOPIC_ARN=$(awslocal sns create-topic --name school-erp-events --query TopicArn --output text)

NOTIFICATION_DLQ_ARN=$(awslocal sqs create-queue --queue-name notification-queue-dlq --query QueueUrl --output text | xargs -I{} awslocal sqs get-queue-attributes --queue-url {} --attribute-names QueueArn --query Attributes.QueueArn --output text)
REPORTING_DLQ_ARN=$(awslocal sqs create-queue --queue-name reporting-queue-dlq --query QueueUrl --output text | xargs -I{} awslocal sqs get-queue-attributes --queue-url {} --attribute-names QueueArn --query Attributes.QueueArn --output text)

# Each queue's redrive policy points at its own DLQ — a message that fails
# processing 3 times lands in the DLQ instead of being retried forever or
# silently dropped (the at-least-once delivery story, completed in Phase 5
# when real consumers exist to actually fail and retry).
NOTIFICATION_QUEUE_URL=$(awslocal sqs create-queue --queue-name notification-queue \
  --attributes "{\"RedrivePolicy\":\"{\\\"deadLetterTargetArn\\\":\\\"$NOTIFICATION_DLQ_ARN\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\"}" \
  --query QueueUrl --output text)
REPORTING_QUEUE_URL=$(awslocal sqs create-queue --queue-name reporting-queue \
  --attributes "{\"RedrivePolicy\":\"{\\\"deadLetterTargetArn\\\":\\\"$REPORTING_DLQ_ARN\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\"}" \
  --query QueueUrl --output text)

NOTIFICATION_QUEUE_ARN=$(awslocal sqs get-queue-attributes --queue-url "$NOTIFICATION_QUEUE_URL" --attribute-names QueueArn --query Attributes.QueueArn --output text)
REPORTING_QUEUE_ARN=$(awslocal sqs get-queue-attributes --queue-url "$REPORTING_QUEUE_URL" --attribute-names QueueArn --query Attributes.QueueArn --output text)

# Fan-out: one SNS topic, two SQS subscribers — Notification and Reporting
# each get their own copy of every event (ADR 0004's "split where contexts
# are read-only/async, never where they share a transaction" reasoning).
awslocal sns subscribe --topic-arn "$TOPIC_ARN" --protocol sqs --notification-endpoint "$NOTIFICATION_QUEUE_ARN"
awslocal sns subscribe --topic-arn "$TOPIC_ARN" --protocol sqs --notification-endpoint "$REPORTING_QUEUE_ARN"

# SES requires sender email verification before it will accept send_email calls.
awslocal ses verify-email-identity --email-address noreply@school.local
