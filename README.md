# comfy-tsc

ComfyUI **自包含**提示词生成器：多风格 Prompt-Writer、Llama 模型选择、提示词收藏。

**不依赖 ideogram-imag**，克隆/下载后复制到 `custom_nodes` 即可使用。

## 安装

```text
1. 复制 comfy-tsc 到 ComfyUI/custom_nodes/

2. 安装依赖（在 comfy-tsc 目录）：
   install.bat
   或：
   <ComfyUI-python> -m pip install -r requirements.txt

3. 配置：
   copy config.example.json config.json
   编辑 config.json（见下方）

4. 重启 ComfyUI
```

## config.json 说明

每人本机路径不同，**必须**自行编辑：

```json
{
  "llama_backend_url": "http://127.0.0.1:1233",
  "llama_port": 1233,
  "llama_server_exe": "路径/llama-server.exe",
  "llama_dir": "llama-server 所在目录",
  "llama_threads": "8",
  "models": {
    "my-model": {
      "label": "显示名称",
      "model": "G:/path/to/model.gguf",
      "mmproj": "G:/path/to/mmproj.gguf",
      "alias": "my-model",
      "ngl": "99",
      "ctx": "8192"
    }
  }
}
```

| 字段 | 说明 |
|------|------|
| `llama_server_exe` | llama.cpp 的 `llama-server.exe` 完整路径 |
| `llama_dir` | 运行 llama-server 的工作目录 |
| `models` | 你的 GGUF 模型列表，可配多个 |
| `mmproj` | 视觉模型投影文件，纯文本模型留空 `""` |
| `ngl` | GPU 层数，`"99"` 或 `"auto"` |

环境变量（可选，覆盖 config）：`LLAMA_BACKEND_URL`、`LLAMA_SERVER_EXE`、`LLAMA_DIR`、`LLAMA_MODEL_KEY`

## 使用（推荐）

重启 ComfyUI 后，浏览器右下角会出现蓝色 **「词」** 按钮。

点击打开 **提示词生成器** 浮动面板（与原控制台界面一致）：

- 选择 / 加载 Llama 模型
- 选风格、填主题、选画幅、可选参考图
- 一键生成 / 复制 / 清空
- 收藏 / 加载 / 删除提示词

也可在节点菜单添加 **「TSC 提示词生成器（控制面板）」**，把 `prompt` 接到 CLIP Text Encode。

旧的 4 个拆分节点仍保留，一般不必再用。

## 节点

| 节点 | 说明 |
|------|------|
| **TSC 提示词 · Llama 模型** | 选模型、加载/卸载/重启 Llama 推理 |
| **TSC 提示词 · 生成** | 15+ 风格，填主题生成提示词 |
| **TSC 提示词 · 收藏** | 保存提示词 |
| **TSC 提示词 · 读取收藏** | 加载 / 删除 / 列出收藏 |

## 工作流

```
TSC 提示词·Llama 模型（加载 Llama 推理）
    → TSC 提示词·生成
    → CLIP Text Encode → 生图
```

## 内置内容

插件自带完整 `prompt_writer/`（风格技能包 + 生成逻辑），**无需**单独安装 MCP 或 ideogram-imag。

唯一外部依赖：**本机 llama-server + GGUF 模型**（在 config.json 里配置路径）。

## 数据文件（不提交 Git）

- `config.json` — 本机配置
- `data/favorites.json` — 收藏的提示词
- `data/llama_model.json` — 上次选用的模型

## 许可证

MIT
