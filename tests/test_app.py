from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.main as main
from app.translations import translate_label


client = TestClient(main.app)


class FakeVertex:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class FakeObjectAnnotation:
    def __init__(self, name: str, score: float) -> None:
        self.name = name
        self.score = score
        self.bounding_poly = SimpleNamespace(
            normalized_vertices=[
                FakeVertex(0.10, 0.20),
                FakeVertex(0.65, 0.20),
                FakeVertex(0.65, 0.84),
                FakeVertex(0.10, 0.84),
            ]
        )


class FakeLabelAnnotation:
    def __init__(self, description: str, score: float) -> None:
        self.description = description
        self.score = score


class FakeVisionResponse:
    def __init__(self) -> None:
        self.error = SimpleNamespace(message="")
        self.localized_object_annotations = [
            FakeObjectAnnotation("Cat", 0.97),
            FakeObjectAnnotation("Pet", 0.42),
        ]
        self.label_annotations = [
            FakeLabelAnnotation("Font", 0.91),
            FakeLabelAnnotation("Screenshot", 0.88),
        ]


class FakeVisionClient:
    def annotate_image(self, request) -> FakeVisionResponse:  # noqa: ANN001
        return FakeVisionResponse()


def test_healthz() -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_runtime_info_works() -> None:
    response = client.get("/api/v1/runtime")

    assert response.status_code == 200
    payload = response.json()
    assert payload["label_language"] == "中文优先（保留英文原词）"


def test_analyze_image_success(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("VISION_API_KEY", "fake-key")
    monkeypatch.setattr(
        main,
        "_analyze_image_with_api_key",
        lambda image_bytes, api_key: main.AnalyzeResponse(  # noqa: ARG005
            labels=[
                main.LabelResult(name="字体", original_name="Font", score=0.91),
                main.LabelResult(name="截图", original_name="Screenshot", score=0.88),
            ],
            objects=[
                main.ObjectResult(
                    name="猫",
                    original_name="Cat",
                    score=0.97,
                    bbox=main.BoundingBox(x_min=0.1, y_min=0.2, x_max=0.65, y_max=0.84),
                )
            ],
        ),
    )

    response = client.post(
        "/api/v1/analyze",
        files={"file": ("cat.png", b"fake-image-bytes", "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["labels"][0]["name"] == "字体"
    assert payload["labels"][0]["original_name"] == "Font"
    assert payload["objects"][0]["name"] == "猫"
    assert payload["objects"][0]["original_name"] == "Cat"


def test_rejects_unsupported_file_type() -> None:
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("notes.txt", b"plain-text", "text/plain")},
    )

    assert response.status_code == 400
    assert "JPG" in response.json()["detail"]


def test_rejects_large_files(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(main, "MAX_FILE_SIZE_BYTES", 4)

    response = client.post(
        "/api/v1/analyze",
        files={"file": ("cat.png", b"12345", "image/png")},
    )

    assert response.status_code == 400
    assert "10MB" in response.json()["detail"]


def test_translate_label_prefers_chinese() -> None:
    assert translate_label("2D barcode") == "二维条码"
    assert translate_label("Screenshot") == "截图"
