# Cloud Run 公网部署

如果你的目标是给老师一个可以直接在线访问的公网网址，推荐走 Cloud Run。

## 部署结果

部署成功后，你会得到一个类似下面的公网地址：

```text
https://vision-object-app-xxxxx-uc.a.run.app
```

老师直接打开这个网址，就可以上传图片并使用识别功能，不需要再输入 API Key。

## 推荐方式：Cloud Shell

在 Google Cloud 控制台右上角打开 Cloud Shell，然后进入项目目录后执行：

```bash
cd ~/gcp-vision-object-app
chmod +x cloudrun/deploy_cloud_run.sh
./cloudrun/deploy_cloud_run.sh <PROJECT_ID>
```

例如：

```bash
./cloudrun/deploy_cloud_run.sh my-gcp-project
```

脚本会自动完成这些事情：

- 启用 Cloud Run、Cloud Build、Secret Manager、Cloud Vision API
- 创建运行时服务账号
- 创建并更新 `vision-api-key` Secret
- 把 `VISION_API_KEY` 注入 Cloud Run
- 部署一个可匿名访问的公网服务
- 最后输出公网 URL

## Windows PowerShell 方式

如果你已经在本机安装了 `gcloud`，也可以运行：

```powershell
.\cloudrun\deploy_cloud_run.ps1 -ProjectId "my-gcp-project"
```

## 运行模式

线上版采用“服务端托管 Vision API Key”的方式：

- 老师访问网页时不需要任何密钥
- API Key 存在 Secret Manager 中
- Cloud Run 从 Secret Manager 注入 `VISION_API_KEY`
- 前端始终只访问同一个公网网址

## 课堂汇报建议

建议你在汇报时展示以下内容：

1. Cloud Run 服务详情页
2. Secret Manager 中的 `vision-api-key`
3. 最终公网 URL
4. 用老师视角直接打开网址并上传图片演示
