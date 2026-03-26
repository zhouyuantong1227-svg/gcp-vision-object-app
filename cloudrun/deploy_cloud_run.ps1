param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,
    [string]$Region = "asia-east1",
    [string]$ServiceName = "vision-object-app",
    [string]$SecretName = "vision-api-key",
    [string]$ServiceAccountName = "vision-cloudrun-sa",
    [string]$VisionApiKey = ""
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "gcloud 未安装。请在 Cloud Shell 或已安装 Google Cloud SDK 的环境中运行。"
}

Write-Host "==> Setting active project"
gcloud config set project $ProjectId | Out-Null

Write-Host "==> Enabling required APIs"
gcloud services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    artifactregistry.googleapis.com `
    secretmanager.googleapis.com `
    vision.googleapis.com | Out-Null

$serviceAccountEmail = "$ServiceAccountName@$ProjectId.iam.gserviceaccount.com"

try {
    gcloud iam service-accounts describe $serviceAccountEmail | Out-Null
}
catch {
    Write-Host "==> Creating Cloud Run runtime service account"
    gcloud iam service-accounts create $ServiceAccountName --display-name "Vision Cloud Run Runtime" | Out-Null
}

try {
    gcloud secrets describe $SecretName | Out-Null
}
catch {
    Write-Host "==> Creating Secret Manager secret"
    gcloud secrets create $SecretName --replication-policy "automatic" | Out-Null
}

if (-not $VisionApiKey) {
    $VisionApiKey = Read-Host "Input Cloud Vision API Key"
}

if (-not $VisionApiKey) {
    throw "Vision API Key 为空，已停止部署。"
}

Write-Host "==> Uploading secret version"
$tmpFile = New-TemporaryFile
Set-Content -Path $tmpFile.FullName -Value $VisionApiKey -NoNewline
gcloud secrets versions add $SecretName --data-file $tmpFile.FullName | Out-Null
Remove-Item $tmpFile.FullName -Force

Write-Host "==> Granting secret access to runtime service account"
gcloud secrets add-iam-policy-binding $SecretName `
    --member "serviceAccount:$serviceAccountEmail" `
    --role "roles/secretmanager.secretAccessor" | Out-Null

Write-Host "==> Deploying Cloud Run service"
gcloud run deploy $ServiceName `
    --source . `
    --region $Region `
    --allow-unauthenticated `
    --service-account $serviceAccountEmail `
    --set-secrets "VISION_API_KEY=$SecretName`:latest" `
    --memory 1Gi `
    --cpu 1 `
    --timeout 60 `
    --max-instances 3 | Out-Null

$serviceUrl = gcloud run services describe $ServiceName --region $Region --format "value(status.url)"

Write-Host ""
Write-Host "Deployment completed."
Write-Host "Public URL: $serviceUrl"
Write-Host "老师可以直接打开这个网址在线使用。"
