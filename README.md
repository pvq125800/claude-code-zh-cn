# Claude Code 桌面版 中文汉化

将 Claude Code 桌面版（Cowork / Code 界面）汉化为简体中文。

> ⚠️ 本项目非官方汉化，仅修改本地界面翻译文件，不修改核心逻辑。

## 快速使用

### 前置条件

- **Windows 10/11**
- **Python 3** — [下载](https://www.python.org/downloads/)（安装时勾选 "Add to PATH"）
- **Claude Code 桌面版** — 从 Microsoft Store 安装

### 安装

1. 下载本仓库（Code → Download ZIP，或 `git clone`）
2. 双击 **`install.bat`**（会自动请求管理员权限）
3. 等待完成，重启 Claude Code

脚本会自动从 [Releases](../../releases) 拉取翻译包 `resources-zh-CN.zip`。如果你的网络访问 GitHub API 不通，手动下载那个 zip 放到 `install.bat` 同目录即可离线安装。

### 卸载

```bash
python install.py --uninstall
```

## 每次 Claude 更新后

Claude 更新会覆盖汉化文件，重新运行 `install.bat` 即可。

## 工作原理

1. 自动扫描 `C:\Program Files\WindowsApps\Claude_*` 定位最新版
2. 获取翻译包（本地 zip 或 GitHub Release），合并内置翻译，并对新版新增 key 回退英文
3. 将结果写入 `ion-dist/i18n/zh-CN.json`、`ion-dist/i18n/statsig/zh-CN.json`、`resources/zh-CN.json`
4. 补丁 JS 语言白名单，加入 `zh-CN` 选项
5. 更新 `AppData/Local/Claude-3p/config.json` 的 locale

早期版本还有一步"硬编码文本替换"，它会连带翻译 JS 源码里的标识符和正则（`Script_Extensions` 等），导致白屏和设置页崩溃，现已彻底移除。

## 翻译覆盖

| 来源 | 条数 | 说明 |
|------|------|------|
| Claude Desktop 汉化包 | 14387 | 共享的前端翻译 |
| Claude Code 专属 | ~2400 | Cowork、Code、远程控制等 |
| **合计** | **16830** | 约 95% 覆盖率 |

## 翻译文本放在哪里

中文文本以 JSON 形式随 **Release 附件** `resources-zh-CN.zip` 分发，不进仓库：

- `frontend-zh-CN.json` — 主界面，key 为哈希
- `shell-zh-CN.json` / `statsig-zh-CN.json` — Shell 与 Statsig 特性文案
- `hardcoded-zh-CN.json` — 英文原文与中文对照表（仅作记录，脚本不再用它做替换）

想补充翻译：下载 zip，对照 Claude 安装目录 `ion-dist/i18n/en-US.json` 找出缺失或仍是英文的 key，改好后把 diff 发到 issue 或 PR。

## 许可与免责

- 本项目采用 MIT 许可，见 [LICENSE](LICENSE)。
- 与 Anthropic 官方无关联。仓库内不含任何账号、密钥或个人路径；`install.py` 只写入本机 Claude 安装目录。
- 若界面出现白屏或设置页报错，先确认没有被 Claude 更新覆盖，重新运行 `install.bat` 即可。

## 致谢

- [claude-desktop-zh-cn](https://github.com/xixu-me/Claude-Desktop-ZH-CN) — 提供基础前端翻译
