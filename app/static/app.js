const allowedTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
const maxSizeBytes = 10 * 1024 * 1024;

const form = document.getElementById("analyze-form");
const imageInput = document.getElementById("image-input");
const analyzeButton = document.getElementById("analyze-button");
const resetButton = document.getElementById("reset-button");
const uploadZone = document.getElementById("upload-zone");
const statusBox = document.getElementById("status");
const previewImage = document.getElementById("preview-image");
const overlay = document.getElementById("overlay");
const canvasShell = document.getElementById("canvas-shell");
const emptyState = document.getElementById("empty-state");
const imageMeta = document.getElementById("image-meta");
const labelList = document.getElementById("label-list");
const objectList = document.getElementById("object-list");
const labelCount = document.getElementById("label-count");
const objectCount = document.getElementById("object-count");
let currentPreviewUrl = null;
let currentObjects = [];

function setStatus(message, state = "idle") {
  statusBox.dataset.state = state;
  statusBox.textContent = message;
  statusBox.classList.toggle("is-hidden", !message);
}

function resetLists() {
  labelList.innerHTML = '<li class="placeholder">暂无结果</li>';
  objectList.innerHTML = '<li class="placeholder">暂无结果</li>';
  labelCount.textContent = "0";
  objectCount.textContent = "0";
}

function revokePreviewUrl() {
  if (currentPreviewUrl) {
    URL.revokeObjectURL(currentPreviewUrl);
    currentPreviewUrl = null;
  }
}

function syncCanvasSize() {
  const displayWidth = previewImage.clientWidth;
  const displayHeight = previewImage.clientHeight;
  if (!displayWidth || !displayHeight) {
    return false;
  }

  overlay.width = displayWidth;
  overlay.height = displayHeight;
  overlay.style.width = `${displayWidth}px`;
  overlay.style.height = `${displayHeight}px`;
  return true;
}

function drawBoxes(objects) {
  const context = overlay.getContext("2d");
  if (!context || !syncCanvasSize()) {
    return;
  }

  context.clearRect(0, 0, overlay.width, overlay.height);
  context.lineWidth = 2;
  context.font = '14px "Segoe UI", "Microsoft YaHei", sans-serif';
  context.textBaseline = "top";

  objects.forEach((item, index) => {
    const hue = (index * 47) % 360;
    const x = item.bbox.x_min * overlay.width;
    const y = item.bbox.y_min * overlay.height;
    const width = (item.bbox.x_max - item.bbox.x_min) * overlay.width;
    const height = (item.bbox.y_max - item.bbox.y_min) * overlay.height;
    const label = `${item.name} ${(item.score * 100).toFixed(1)}%`;

    context.strokeStyle = `hsla(${hue}, 86%, 44%, 0.95)`;
    context.fillStyle = `hsla(${hue}, 86%, 44%, 0.14)`;
    context.strokeRect(x, y, width, height);
    context.fillRect(x, y, width, height);

    const textWidth = context.measureText(label).width + 18;
    const textY = Math.max(0, y - 28);
    context.fillStyle = `hsla(${hue}, 86%, 32%, 0.94)`;
    context.fillRect(x, textY, textWidth, 24);
    context.fillStyle = "#ffffff";
    context.fillText(label, x + 9, textY + 4);
  });
}

function createResultItem(item, showBox = false) {
  const listItem = document.createElement("li");
  listItem.className = "result-item";
  const secondaryName = item.original_name && item.original_name !== item.name
    ? item.original_name
    : "英文原词与中文一致";
  const extra = showBox
    ? `定位: [${item.bbox.x_min.toFixed(2)}, ${item.bbox.y_min.toFixed(2)}]`
    : "标签结果";

  listItem.innerHTML = `
    <div class="result-top">
      <span class="result-name">${item.name}</span>
      <span class="result-meta">${(item.score * 100).toFixed(1)}%</span>
    </div>
    <div class="result-subtitle">${secondaryName}</div>
    <div class="result-meta">${extra}</div>
  `;
  return listItem;
}

function renderResults(data) {
  currentObjects = data.objects ?? [];
  labelList.innerHTML = "";
  objectList.innerHTML = "";

  if (!data.labels.length) {
    labelList.innerHTML = '<li class="placeholder">暂无结果</li>';
  } else {
    data.labels.forEach((label) => {
      labelList.appendChild(createResultItem(label));
    });
  }

  if (!data.objects.length) {
    objectList.innerHTML = '<li class="placeholder">暂无结果</li>';
  } else {
    data.objects.forEach((objectItem) => {
      objectList.appendChild(createResultItem(objectItem, true));
    });
  }

  labelCount.textContent = String(data.labels.length);
  objectCount.textContent = String(data.objects.length);
  drawBoxes(currentObjects);
}

function resetAll() {
  revokePreviewUrl();
  form.reset();
  analyzeButton.disabled = true;
  currentObjects = [];
  imageMeta.textContent = "";
  previewImage.removeAttribute("src");
  canvasShell.classList.add("empty");
  emptyState.hidden = false;
  const context = overlay.getContext("2d");
  if (context) {
    context.clearRect(0, 0, overlay.width, overlay.height);
  }
  overlay.removeAttribute("width");
  overlay.removeAttribute("height");
  resetLists();
  setStatus("", "idle");
}

function validateFile(file) {
  if (!file) {
    return "请选择一张图片。";
  }
  if (!allowedTypes.has(file.type)) {
    return "仅支持 JPG、PNG、WEBP 图片。";
  }
  if (file.size > maxSizeBytes) {
    return "图片不能超过 10MB。";
  }
  return null;
}

function handleFileSelection(file) {
  const error = validateFile(file);
  if (error) {
    resetAll();
    setStatus(error, "error");
    return;
  }

  revokePreviewUrl();
  currentPreviewUrl = URL.createObjectURL(file);
  previewImage.src = currentPreviewUrl;
  previewImage.onload = () => {
    canvasShell.classList.remove("empty");
    emptyState.hidden = true;
    imageMeta.textContent = `${file.name} | ${(file.size / 1024 / 1024).toFixed(2)} MB`;
    drawBoxes(currentObjects);
  };

  analyzeButton.disabled = false;
  currentObjects = [];
  resetLists();
  setStatus("", "idle");
}

imageInput.addEventListener("change", (event) => {
  handleFileSelection(event.target.files?.[0] ?? null);
});

["dragenter", "dragover"].forEach((eventName) => {
  uploadZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadZone.classList.add("drag-over");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  uploadZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadZone.classList.remove("drag-over");
  });
});

uploadZone.addEventListener("drop", (event) => {
  const file = event.dataTransfer?.files?.[0];
  if (file) {
    imageInput.files = event.dataTransfer.files;
    handleFileSelection(file);
  }
});

window.addEventListener("resize", () => drawBoxes(currentObjects));

resetButton.addEventListener("click", () => {
  resetAll();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = imageInput.files?.[0];
  const error = validateFile(file);
  if (error) {
    setStatus(error, "error");
    return;
  }

  analyzeButton.disabled = true;
  setStatus("正在上传图片并请求 Cloud Vision API，请稍候...", "loading");

  try {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("/api/v1/analyze", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "识别失败，请稍后重试。");
    }

    renderResults(data);
    setStatus("识别完成，结果已更新到页面。", "success");
  } catch (errorInstance) {
    currentObjects = [];
    drawBoxes(currentObjects);
    setStatus(errorInstance.message || "识别失败，请重试。", "error");
  } finally {
    analyzeButton.disabled = false;
  }
});

resetAll();
