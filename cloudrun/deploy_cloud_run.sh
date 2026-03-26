#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-}"
REGION="${2:-asia-east1}"
SERVICE_NAME="${3:-vision-object-app}"
SECRET_NAME="${4:-vision-api-key}"
SERVICE_ACCOUNT_NAME="${5:-vision-cloudrun-sa}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: ./cloudrun/deploy_cloud_run.sh <PROJECT_ID> [REGION] [SERVICE_NAME] [SECRET_NAME] [SERVICE_ACCOUNT_NAME]"
  exit 1
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud is required. Run this script in Cloud Shell or install Google Cloud SDK first."
  exit 1
fi

echo "==> Setting active project"
gcloud config set project "$PROJECT_ID" >/dev/null

echo "==> Enabling required APIs"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  vision.googleapis.com

SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" >/dev/null 2>&1; then
  echo "==> Creating Cloud Run runtime service account"
  gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
    --display-name="Vision Cloud Run Runtime"
fi

if ! gcloud secrets describe "$SECRET_NAME" >/dev/null 2>&1; then
  echo "==> Creating Secret Manager secret"
  gcloud secrets create "$SECRET_NAME" --replication-policy="automatic"
fi

if [[ -z "${VISION_API_KEY:-}" ]]; then
  read -rsp "Input Cloud Vision API Key: " VISION_API_KEY
  echo
fi

if [[ -z "${VISION_API_KEY:-}" ]]; then
  echo "VISION_API_KEY is empty. Aborting."
  exit 1
fi

echo "==> Uploading secret version"
printf "%s" "$VISION_API_KEY" | gcloud secrets versions add "$SECRET_NAME" --data-file=-

echo "==> Granting secret access to runtime service account"
gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/secretmanager.secretAccessor" >/dev/null

echo "==> Deploying Cloud Run service"
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --service-account "$SERVICE_ACCOUNT_EMAIL" \
  --set-secrets "VISION_API_KEY=${SECRET_NAME}:latest" \
  --memory 1Gi \
  --cpu 1 \
  --timeout 60 \
  --max-instances 3

SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"

echo
echo "Deployment completed."
echo "Public URL: ${SERVICE_URL}"
echo "Teacher can open this URL directly and use the app online."
