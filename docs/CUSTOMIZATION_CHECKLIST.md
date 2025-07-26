# 🎨 定制化清单

## 1. 应用名称和品牌
- [ ] `src/lib/constants.ts` → 第4行 APP_NAME
- [ ] `.env` → 添加 `WEBUI_NAME=你的应用名称`
- [ ] `static/manifest.json` → name 和 short_name

## 2. 图标和Logo
- [ ] `static/favicon.ico`
- [ ] `static/favicon.png`
- [ ] `static/logo.png`
- [ ] `static/icon-192.png`
- [ ] `static/icon-512.png`
- [ ] `backend/open_webui/static/favicon.ico`
- [ ] `backend/open_webui/static/logo.png`

## 3. 页面标题和描述
- [ ] `src/app.html` → title 和 description
- [ ] `static/manifest.json` → description

## 4. 主题和样式
- [ ] `static/custom.css` → 自定义样式
- [ ] `src/tailwind.css` → 主题色彩

## 5. 默认设置
- [ ] 管理员界面 → 设置 → 界面 → 横幅
- [ ] 管理员界面 → 设置 → 通用 → 默认模型
- [ ] `.env` 文件中的其他配置

## 6. 构建和部署
```bash
# 前端构建
npm run build

# Docker构建
docker build -t your-company/emohaa-webui:latest .

# 部署运行
docker run -d -p 3000:8080 \
  -e WEBUI_NAME="你的应用名称" \
  -v open-webui:/app/backend/data \
  your-company/emohaa-webui:latest
```

## 7. 验证清单
- [ ] 网站标题显示正确
- [ ] favicon显示正确  
- [ ] logo显示正确
- [ ] 应用名称显示正确
- [ ] 横幅公告显示正确
- [ ] PWA安装正常