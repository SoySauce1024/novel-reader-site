# Novel Reader Site

这是《万古第一神》的公网静态阅读站，适合部署到 GitHub Pages。

## 本地生成

从写作仓库读取 Markdown 章节并生成静态网站：

```bash
python3 scripts/build_site.py --source ../store/novel --output docs
```

## 本地预览

```bash
python3 -m http.server 8001 -d docs
```

浏览器打开：`http://127.0.0.1:8001`

## GitHub Pages 设置

1. 进入仓库 `Settings` → `Pages`
2. `Source` 选择 `Deploy from a branch`
3. `Branch` 选择 `main`
4. 目录选择 `/docs`
5. 保存后等待部署完成

公网地址通常是：

```text
https://soysauce1024.github.io/novel-reader-site/
```

