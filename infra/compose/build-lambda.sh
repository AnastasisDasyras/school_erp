#!/usr/bin/env bash
# Builds the notification Lambda deployment zip that localstack-init.sh deploys.
#
# We package a plain zip for the python3.12 Lambda runtime (rather than a
# container image). The zip must contain our source PLUS the third-party deps
# that are NOT already in the Lambda runtime. boto3 IS in the runtime, so it's
# excluded to keep the zip small.
#
# Run this before `docker compose up` (or whenever the notification source
# changes). Output: infra/compose/notification-lambda.zip
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NOTIFICATION_SRC="$HERE/../../services/notification/src"
BUILD_DIR="$HERE/.lambda-build"
# Output into a directory that docker-compose mounts into the localstack
# container (a dir mount survives host-side rebuilds; a single-file mount does
# not on Docker Desktop).
DIST_DIR="$HERE/lambda-dist"
ZIP_OUT="$DIST_DIR/notification-lambda.zip"

# Deps needed at runtime that aren't in the Lambda python3.12 runtime.
# (boto3 is provided by the runtime; omit it.) OpenTelemetry isn't imported by
# the Lambda path (we don't call setup_tracing in lambda_handler), so it's
# omitted too — keeps the zip lean.
DEPS=(pybreaker pydantic-settings pydantic structlog tenacity)

echo "==> Cleaning build dir"
rm -rf "$BUILD_DIR" "$ZIP_OUT"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

echo "==> Installing deps into build dir (targeting the Lambda Linux runtime)"
# pydantic-core ships a COMPILED native extension. The zip runs in the Lambda
# runtime container (Linux x86_64), not on this host — so we must fetch the
# manylinux/x86_64 cp312 wheels, not the host's (e.g. macOS arm64) build.
# --only-binary=:all: forces wheel use so nothing is compiled against the host.
python3.12 -m pip install --quiet --target "$BUILD_DIR" \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  "${DEPS[@]}"

echo "==> Copying notification source"
cp -r "$NOTIFICATION_SRC/notification" "$BUILD_DIR/notification"

echo "==> Zipping"
(cd "$BUILD_DIR" && zip -q -r "$ZIP_OUT" .)

rm -rf "$BUILD_DIR"
echo "==> Built $ZIP_OUT ($(du -h "$ZIP_OUT" | cut -f1))"
