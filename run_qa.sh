#!/usr/bin/env bash
set -e

ENV=$1
BASE_URL=$2
TEST_SUITE=$3

AWS_REGION="us-west-2"
ECR_REPO="qa-automation-ci"
SECRET_ID="qa/staging/credentials"
S3_BUCKET="skoopin-mercato-stg-us-west-2"
BUILD_NUMBER=${4:-$(date +%Y%m%d%H%M%S)}
DEPLOYED_BRANCH=${5:-unknown}
DEPLOYED_COMMIT=${6:-unknown}

# Resolve ECR URI dynamically
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region $AWS_REGION)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"

echo "==> Logging into ECR"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI

echo "==> Pulling latest image"
docker pull $ECR_URI:latest

echo "==> Fetching secrets"
SECRET=$(aws secretsmanager get-secret-value --region $AWS_REGION --secret-id $SECRET_ID --query SecretString --output text)
COGNITO_CLIENT_ID=$(echo "$SECRET" | jq -r '.["cognito-client-id"]')
API_USERNAME=$(echo "$SECRET"      | jq -r '.["api-username"]')
API_PASSWORD=$(echo "$SECRET"      | jq -r '.["api-password"]')
UI_EMAIL=$(echo "$SECRET"          | jq -r '.["ui-email"]')
UI_PASSWORD=$(echo "$SECRET"       | jq -r '.["ui-password"]')
XRAY_CLIENT_ID=$(echo "$SECRET"     | jq -r '.["xray-client-id"] // ""')
XRAY_CLIENT_SECRET=$(echo "$SECRET" | jq -r '.["xray-client-secret"] // ""')

MARKER_FLAG=""
if [ "$TEST_SUITE" != "all" ]; then
    MARKER_FLAG="-m $TEST_SUITE"
fi

echo "==> Running tests (suite: $TEST_SUITE, env: $ENV)"
WORKDIR="/tmp/qa-run-$BUILD_NUMBER"
mkdir -p $WORKDIR

CID=$(docker create \
    -e ENV="$ENV" \
    -e BASE_URL="$BASE_URL" \
    -e COGNITO_CLIENT_ID="$COGNITO_CLIENT_ID" \
    -e API_USERNAME="$API_USERNAME" \
    -e API_PASSWORD="$API_PASSWORD" \
    -e SKOOPIN_KITCHEN_SAPNA_EMAIL="$UI_EMAIL" \
    -e SKOOPIN_KITCHEN_SAPNA_PASSWORD="$UI_PASSWORD" \
    -e DEPLOYED_BRANCH="$DEPLOYED_BRANCH" \
    -e DEPLOYED_COMMIT="$DEPLOYED_COMMIT" \
    -e XRAY_CLIENT_ID="$XRAY_CLIENT_ID" \
    -e XRAY_CLIENT_SECRET="$XRAY_CLIENT_SECRET" \
    -e BUILD_NUMBER="$BUILD_NUMBER" \
    $ECR_URI:latest \
    bash -c "pytest dashboard/tests/ --ignore=dashboard/tests/test_seed.py -s $MARKER_FLAG --alluredir=allure-results --clean-alluredir; exit \$?")

docker start $CID
EXIT=$(docker wait $CID)
docker logs $CID
docker cp $CID:/workspace/allure-results $WORKDIR/ 2>/dev/null || true
docker cp $CID:/workspace/reports        $WORKDIR/ 2>/dev/null || true
docker rm $CID

echo "==> Uploading reports to S3"
aws s3 sync $WORKDIR/reports/ s3://$S3_BUCKET/QA-Reports/$BUILD_NUMBER/reports/ --region $AWS_REGION || true

echo "==> Cleaning up"
rm -rf $WORKDIR
docker system prune -f || true

exit $EXIT
