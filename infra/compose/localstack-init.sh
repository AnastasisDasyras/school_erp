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

# ── Phase 12: AWS Lambda notification path (LocalStack demo) ─────────────────
# A SECOND consumer for the same AttendanceRecorded events, delivered as a
# Lambda instead of the long-running container. Its own queue + DLQ keeps it
# fully isolated from the container consumer's notification-queue, so both fire
# for every event (the container-vs-serverless side-by-side demo).

LAMBDA_DLQ_ARN=$(awslocal sqs create-queue --queue-name notification-lambda-queue-dlq --query QueueUrl --output text | xargs -I{} awslocal sqs get-queue-attributes --queue-url {} --attribute-names QueueArn --query Attributes.QueueArn --output text)

LAMBDA_QUEUE_URL=$(awslocal sqs create-queue --queue-name notification-lambda-queue \
  --attributes "{\"RedrivePolicy\":\"{\\\"deadLetterTargetArn\\\":\\\"$LAMBDA_DLQ_ARN\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\"}" \
  --query QueueUrl --output text)
LAMBDA_QUEUE_ARN=$(awslocal sqs get-queue-attributes --queue-url "$LAMBDA_QUEUE_URL" --attribute-names QueueArn --query Attributes.QueueArn --output text)

# Fan-out: same SNS topic, a third SQS subscriber feeding the Lambda's queue.
awslocal sns subscribe --topic-arn "$TOPIC_ARN" --protocol sqs --notification-endpoint "$LAMBDA_QUEUE_ARN"

# Create the function from the prebuilt zip (mounted at /tmp by docker-compose;
# built by build-lambda.sh). The role ARN is a placeholder — LocalStack does
# not enforce IAM permissions. Env vars point the handler at LocalStack SES.
awslocal lambda create-function \
  --function-name notification-lambda \
  --runtime python3.12 \
  --handler notification.lambda_handler.handler \
  --role arn:aws:iam::000000000000:role/lambda-role \
  --zip-file fileb:///opt/lambda-dist/notification-lambda.zip \
  --timeout 30 \
  --environment "Variables={AWS_ENDPOINT_URL=http://localstack:4566,AWS_REGION=us-east-1,AWS_ACCESS_KEY_ID=test,AWS_SECRET_ACCESS_KEY=test,SES_FROM_ADDRESS=noreply@school.local}"

awslocal lambda wait function-active-v2 --function-name notification-lambda

# The event-source mapping is what makes this "serverless": AWS (LocalStack)
# polls notification-lambda-queue and invokes the function per batch. This
# replaces the hand-rolled receive_message loop the container consumer runs.
awslocal lambda create-event-source-mapping \
  --function-name notification-lambda \
  --event-source-arn "$LAMBDA_QUEUE_ARN" \
  --batch-size 10
