#!/usr/bin/env bash
# Deploy the Tableau Analysis Tool to Cloud Run, restricted to Mastech staff.
#
# Region is asia-south1: the org policy constraints/gcp.resourceLocations on
# this project allows only asia-south1 and us-central1. Anything else fails
# at validation with FAILED_PRECONDITION.
#
# Prerequisites (see DEPLOY.md): the APIs below must be enabled and the
# deploying account needs run.admin + iam.serviceAccountUser + iap.admin.
set -euo pipefail

PROJECT="${PROJECT:-ctoteam}"
REGION="${REGION:-asia-south1}"
SERVICE="${SERVICE:-tableau-analyzer}"

echo ">> Enabling required APIs (no-op if already enabled)"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  iap.googleapis.com \
  --project="$PROJECT"

echo ">> Building from source and deploying"
# max-instances=1 is deliberate: the job store is in-process memory, so a
# second instance would not see a user's uploaded workbook. Raise this only
# after the store moves to shared state (GCS/Redis).
# no-allow-unauthenticated keeps the service private; IAP below grants access.
gcloud run deploy "$SERVICE" \
  --source . \
  --quiet \
  --project="$PROJECT" \
  --region="$REGION" \
  --platform=managed \
  --no-allow-unauthenticated \
  --max-instances=1 \
  --min-instances=0 \
  --memory=4Gi \
  --cpu=2 \
  --timeout=900 \
  --concurrency=40 \
  --set-env-vars=ANALYZER_JOB_TTL=3600

echo ">> Enabling IAP on the service"
gcloud beta run services update "$SERVICE" \
  --project="$PROJECT" \
  --region="$REGION" \
  --iap

echo ">> Granting every Mastech account access through IAP"
gcloud beta iap web add-iam-policy-binding \
  --project="$PROJECT" \
  --resource-type=cloud-run \
  --service="$SERVICE" \
  --region="$REGION" \
  --member="domain:mastechdigital.com" \
  --role="roles/iap.httpsResourceAccessor"

echo
echo ">> Done. URL:"
gcloud run services describe "$SERVICE" \
  --project="$PROJECT" --region="$REGION" --format="value(status.url)"
