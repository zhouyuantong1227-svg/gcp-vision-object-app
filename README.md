# GCP Vision Object App

基于 Google Cloud Vision API 的图片目标识别课程项目。

项目现在支持两种交付形态：

- 本地演示版：双击启动器或 EXE，本机输入 API Key 后使用
- 公网在线版：部署到 Cloud Run，生成公网 URL，直接通过网址访问

## 1. 最终交付方式：公网 URL

如果你的目标是“直接打开网址就能在线使用”，推荐部署到 Cloud Run。

部署完成后会得到一个类似下面的公网地址：

```text
https://vision-object-app-xxxxx-uc.a.run.app
```

访问这个网址时：

- 不需要安装任何软件
- 不需要输入 API Key
- 直接上传图片即可识别

详细步骤见：

- [cloudrun/README.md](cloudrun/README.md)
- [cloudrun/deploy_cloud_run.sh](cloudrun/deploy_cloud_run.sh)
- [cloudrun/deploy_cloud_run.ps1](cloudrun/deploy_cloud_run.ps1)

## 2. Cloud Run 一键部署

在 Google Cloud Cloud Shell 中执行：

```bash
cd ~/gcp-vision-object-app
chmod +x cloudrun/deploy_cloud_run.sh
./cloudrun/deploy_cloud_run.sh <PROJECT_ID>
```

脚本会自动：

- 启用 Cloud Run、Cloud Build、Secret Manager、Cloud Vision API
- 创建运行时服务账号
- 创建并更新 `vision-api-key` Secret
- 把 `VISION_API_KEY` 注入 Cloud Run
- 部署为公网可访问服务
- 输出最终公网 URL

## 3. 本地演示版

如果还需要在本机答辩演示，可以继续使用桌面启动器版本。

### 双击启动

1. 双击 `start_vision_app.cmd`
2. 第一次运行会自动创建 `.venv` 并安装依赖
3. 启动器窗口出现后，在输入框里填入 `Cloud Vision API Key`
4. 点击“启动应用”
5. 浏览器会自动打开识别页面

密钥会保存在 `.env.local`，下次启动会自动填充。

### 打包成 EXE

1. 双击 `build_vision_app_exe.cmd`
2. 构建完成后，生成文件在 `dist\VisionObjectApp.exe`
3. 双击该 EXE，会先打开一个桌面启动器界面
4. 输入 API Key 后，点击“启动应用”
5. 浏览器自动打开本地识别页面

## 4. 本地开发运行

```powershell
cd D:\Aaaaalearning\HOMEWORK\云计算\gcp-vision-object-app
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python launcher.py
```

## 5. 容器与云端说明

- `Dockerfile`
  现在已改成跟随 `PORT` 环境变量启动，适合 Cloud Run。
- `.dockerignore`
  已排除本地打包产物、汇报材料和虚拟环境，减少云端构建体积。
- `k8s/`
  保留了原来的 GKE 结构；如果只看最终可访问网址，Cloud Run 会更直接。

## 6. 运行鉴权方式

当前线上推荐方式是“服务端托管 API Key”：

- 本地版：启动器把 `VISION_API_KEY` 写入 `.env.local`
- 线上版：Cloud Run 从 Secret Manager 注入 `VISION_API_KEY`

这样访问时不需要任何凭证。

## 7. 文件说明

- `app/main.py`
  FastAPI 后端，负责调用 Vision API、返回中文标签和目标定位结果。
- `app/translations.py`
  英文标签到中文的本地映射。
- `launcher.py`
  本地启动器窗口。
- `cloudrun/deploy_cloud_run.sh`
  Cloud Shell 推荐部署脚本，部署完成后输出公网 URL。
- `cloudrun/deploy_cloud_run.ps1`
  Windows PowerShell 部署脚本。
- `vision_app.spec`
  PyInstaller 打包配置。

## 8. 语法校验

```powershell
python -m compileall app tests launcher.py
```
