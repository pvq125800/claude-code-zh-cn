# Claude Code 桌面版 中文汉化

将 Claude Code 桌面版（Cowork / Code 界面）汉化为简体中文。

> ⚠️ 本项目非官方汉化，仅修改本地界面翻译文件，不修改核心逻辑。

## 截图

汉化前（英文） | 汉化后（中文）
:-:|:-:
英文界面 | 覆盖 95% 的界面文本

## 快速使用

### 前置条件

- **Windows 10/11**
- **Python 3** — [下载](https://www.python.org/downloads/)（安装时勾选 "Add to PATH"）
- **Claude Code 桌面版** — 从 Microsoft Store 安装

### 安装

1. 下载本仓库（Code → Download ZIP，或 `git clone`）
2. 双击 **`install.bat`**（会自动请求管理员权限）
3. 等待完成，重启 Claude Code

### 卸载

```bash
python install.py --uninstall
```

## 每次 Claude 更新后

Claude 更新会覆盖汉化文件，重新运行 `install.bat` 即可。

## 工作原理

1. 自动扫描 `C:\Program Files\WindowsApps\Claude_*` 定位最新版
2. 将内置的 16830 条中文翻译写入 `ion-dist/i18n/zh-CN.json`
3. 补丁 JS 语言白名单，加入 `zh-CN` 选项
4. 更新 `AppData/Local/Claude-3p/config.json` 的 locale

## 翻译覆盖

| 来源 | 条数 | 说明 |
|------|------|------|
| Claude Desktop 汉化包 | 14387 | 共享的前端翻译 |
| Claude Code 专属 | ~2400 | Cowork、Code、远程控制等 |
| **合计** | **16830** | 约 95% 覆盖率 |

## 贡献翻译

翻译文件为 `resources/frontend-zh-CN.json`，key 为哈希值。若想补充翻译：

1. 找到英文 `en-US.json`（在 Claude 安装目录 `ion-dist/i18n/` 下）
2. 对比缺失的 key，翻译后加入 `frontend-zh-CN.json`
3. 提交 PR

## 许可与免责

- 本项目采用 MIT 许可，见 [LICENSE](LICENSE)。
- 与 Anthropic 官方无关联。仓库内不含任何账号、密钥或个人路径；`install.py` 只写入本机 Claude 安装目录。
- 若界面出现白屏或设置页报错，先确认没有被 Claude 更新覆盖，重新运行 `install.bat` 即可。

## 致谢

- [claude-desktop-zh-cn](https://github.com/xixu-me/Claude-Desktop-ZH-CN) — 提供基础前端翻译
