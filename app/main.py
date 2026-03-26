from __future__ import annotations

import base64
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.translations import translate_label

try:
    from google.api_core.exceptions import GoogleAPICallError, RetryError
    from google.cloud import vision
except ImportError:  # pragma: no cover - optional for API-key-only local runs
    GoogleAPICallError = None
    RetryError = None
    vision = None

if getattr(sys, "frozen", False):  # pragma: no cover - used by packaged EXE
    STATIC_DIR = Path(getattr(sys, "_MEIPASS")) / "app" / "static"
else:
    STATIC_DIR = Path(__file__).resolve().parent / "static"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_LABELS = 5
OBJECT_SCORE_THRESHOLD = 0.50
VISION_API_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"
VISION_API_TIMEOUT_SECONDS = 30

logger = logging.getLogger(__name__)


class BoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class LabelResult(BaseModel):
    name: str
    original_name: str
    score: float


class ObjectResult(BaseModel):
    name: str
    original_name: str
    score: float
    bbox: BoundingBox


class AnalyzeResponse(BaseModel):
    labels: list[LabelResult]
    objects: list[ObjectResult]


class RuntimeInfo(BaseModel):
    auth_mode: str
    label_language: str
    max_file_size_mb: int


app = FastAPI(
    title="GCP Vision Object Detection App",
    version="1.2.0",
    summary="Upload an image and detect labels plus localized objects with Cloud Vision API.",
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def get_runtime_auth_mode() -> str:
    return "API Key" if os.getenv("VISION_API_KEY") else "ADC / Service Account"


def get_vision_client() -> Any:
    if vision is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "当前环境未安装 google-cloud-vision。"
                "如果你想用 API Key，请先设置 VISION_API_KEY；"
                "如果你想用服务账号，请先执行 pip install -r requirements-gcp.txt。"
            ),
        )
    return vision.ImageAnnotatorClient()


def _is_supported_image(upload_file: UploadFile) -> bool:
    suffix = Path(upload_file.filename or "").suffix.lower()
    return upload_file.content_type in ALLOWED_CONTENT_TYPES or suffix in ALLOWED_SUFFIXES


def _localize_name(name: str) -> tuple[str, str]:
    display_name = translate_label(name)
    return display_name, name


def _build_bbox(normalized_vertices: list[Any]) -> BoundingBox:
    if not normalized_vertices:
        return BoundingBox(x_min=0.0, y_min=0.0, x_max=0.0, y_max=0.0)

    xs = [float(vertex.x) for vertex in normalized_vertices]
    ys = [float(vertex.y) for vertex in normalized_vertices]
    return BoundingBox(
        x_min=max(0.0, min(xs)),
        y_min=max(0.0, min(ys)),
        x_max=min(1.0, max(xs)),
        y_max=min(1.0, max(ys)),
    )


def _build_bbox_from_dicts(normalized_vertices: list[dict[str, float]]) -> BoundingBox:
    if not normalized_vertices:
        return BoundingBox(x_min=0.0, y_min=0.0, x_max=0.0, y_max=0.0)

    xs = [float(vertex.get("x", 0.0)) for vertex in normalized_vertices]
    ys = [float(vertex.get("y", 0.0)) for vertex in normalized_vertices]
    return BoundingBox(
        x_min=max(0.0, min(xs)),
        y_min=max(0.0, min(ys)),
        x_max=min(1.0, max(xs)),
        y_max=min(1.0, max(ys)),
    )


async def _read_and_validate_file(upload_file: UploadFile) -> bytes:
    if not upload_file.filename:
        raise HTTPException(status_code=400, detail="请选择一张图片后再上传。")

    if not _is_supported_image(upload_file):
        raise HTTPException(status_code=400, detail="仅支持 JPG、PNG、WEBP 格式图片。")

    content = await upload_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空，请重新选择图片。")

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="图片不能超过 10MB，请压缩后重试。")

    return content


def _build_label_result(original_name: str, score: float) -> LabelResult:
    localized_name, original = _localize_name(original_name)
    return LabelResult(name=localized_name, original_name=original, score=float(score))


def _build_object_result(original_name: str, score: float, bbox: BoundingBox) -> ObjectResult:
    localized_name, original = _localize_name(original_name)
    return ObjectResult(
        name=localized_name,
        original_name=original,
        score=float(score),
        bbox=bbox,
    )


def analyze_image(image_bytes: bytes) -> AnalyzeResponse:
    api_key = os.getenv("VISION_API_KEY")
    if api_key:
        return _analyze_image_with_api_key(image_bytes, api_key)

    return _analyze_image_with_adc(image_bytes)


def _analyze_image_with_adc(image_bytes: bytes) -> AnalyzeResponse:
    if vision is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "当前环境缺少 google-cloud-vision。"
                "本地使用 API Key 时请设置 VISION_API_KEY；"
                "服务账号模式请先安装 requirements-gcp.txt。"
            ),
        )

    client = get_vision_client()
    request = vision.AnnotateImageRequest(
        image=vision.Image(content=image_bytes),
        features=[
            vision.Feature(type_=vision.Feature.Type.OBJECT_LOCALIZATION),
            vision.Feature(type_=vision.Feature.Type.LABEL_DETECTION, max_results=MAX_LABELS),
        ],
    )

    try:
        response = client.annotate_image(request=request)
    except Exception as exc:  # pragma: no cover - external dependency path
        google_error_types = tuple(
            error_type for error_type in (GoogleAPICallError, RetryError) if error_type is not None
        )
        if google_error_types and isinstance(exc, google_error_types):
            logger.exception("Cloud Vision request failed")
            raise HTTPException(status_code=502, detail="Cloud Vision API 调用失败，请稍后重试。") from exc
        logger.exception("Unexpected error while calling Cloud Vision")
        raise HTTPException(status_code=500, detail="服务发生异常，请检查云端凭证和 API 配置。") from exc

    if response.error.message:
        logger.error("Cloud Vision API returned an error: %s", response.error.message)
        raise HTTPException(
            status_code=502,
            detail=f"Cloud Vision API 返回错误: {response.error.message}",
        )

    labels = sorted(
        (
            _build_label_result(annotation.description, float(annotation.score))
            for annotation in response.label_annotations
        ),
        key=lambda item: item.score,
        reverse=True,
    )[:MAX_LABELS]

    objects = sorted(
        (
            _build_object_result(
                annotation.name,
                float(annotation.score),
                _build_bbox(annotation.bounding_poly.normalized_vertices),
            )
            for annotation in response.localized_object_annotations
            if float(annotation.score) >= OBJECT_SCORE_THRESHOLD
        ),
        key=lambda item: item.score,
        reverse=True,
    )

    return AnalyzeResponse(labels=labels, objects=objects)


def _analyze_image_with_api_key(image_bytes: bytes, api_key: str) -> AnalyzeResponse:
    payload = {
        "requests": [
            {
                "image": {"content": base64.b64encode(image_bytes).decode("utf-8")},
                "features": [
                    {"type": "OBJECT_LOCALIZATION"},
                    {"type": "LABEL_DETECTION", "maxResults": MAX_LABELS},
                ],
            }
        ]
    }
    request = urllib_request.Request(
        url=f"{VISION_API_ENDPOINT}?key={api_key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=VISION_API_TIMEOUT_SECONDS) as response:
            raw_payload = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        logger.exception("Vision API key request failed: %s", error_body)
        raise HTTPException(
            status_code=502,
            detail="Vision API Key 调用失败，请检查该 Key 是否已启用 Cloud Vision API。",
        ) from exc
    except urllib_error.URLError as exc:
        logger.exception("Vision API key request network failure")
        raise HTTPException(status_code=502, detail="无法连接到 Cloud Vision API，请稍后重试。") from exc

    response_payload = (raw_payload.get("responses") or [{}])[0]
    if response_payload.get("error", {}).get("message"):
        message = response_payload["error"]["message"]
        logger.error("Cloud Vision API returned an error: %s", message)
        raise HTTPException(status_code=502, detail=f"Cloud Vision API 返回错误: {message}")

    labels = sorted(
        (
            _build_label_result(annotation.get("description", ""), float(annotation.get("score", 0.0)))
            for annotation in response_payload.get("labelAnnotations", [])
            if annotation.get("description")
        ),
        key=lambda item: item.score,
        reverse=True,
    )[:MAX_LABELS]

    objects = sorted(
        (
            _build_object_result(
                annotation.get("name", ""),
                float(annotation.get("score", 0.0)),
                _build_bbox_from_dicts(
                    annotation.get("boundingPoly", {}).get("normalizedVertices", [])
                ),
            )
            for annotation in response_payload.get("localizedObjectAnnotations", [])
            if annotation.get("name") and float(annotation.get("score", 0.0)) >= OBJECT_SCORE_THRESHOLD
        ),
        key=lambda item: item.score,
        reverse=True,
    )

    return AnalyzeResponse(labels=labels, objects=objects)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/runtime", response_model=RuntimeInfo)
async def runtime_info() -> RuntimeInfo:
    return RuntimeInfo(
        auth_mode=get_runtime_auth_mode(),
        label_language="中文优先（保留英文原词）",
        max_file_size_mb=MAX_FILE_SIZE_BYTES // (1024 * 1024),
    )


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile = File(...)) -> AnalyzeResponse:
    image_bytes = await _read_and_validate_file(file)
    return analyze_image(image_bytes)
