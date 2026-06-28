#!/usr/bin/env bash
# Runs automatically when the LocalStack container is ready (mounted into
# /etc/localstack/init/ready.d/). Creates the messaging infra used from Phase 4 onward.
set -euo pipefail

awslocal sns create-topic --name school-erp-events
awslocal sqs create-queue --queue-name notification-queue
awslocal sqs create-queue --queue-name reporting-queue
awslocal sqs create-queue --queue-name notification-queue-dlq
awslocal sqs create-queue --queue-name reporting-queue-dlq
