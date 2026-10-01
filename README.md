# Claude Code 桌面版 中文汉化

把 Microsoft Store 版 Claude Code 桌面版（Cowork / Code 界面）汉化为简体中文。双击一次就好，Claude 每次自动更新后重跑一次。

> ⚠️ 非官方汉化。只写入本地界面翻译文件与三处语言开关，不修改核心逻辑、不替换任何 JS 标识符。

## 效果

| 范围 | 覆盖 |
|------|------|
| 前端界面（`ion-dist/i18n`） | 31,749 / 32,243 条，**98%** |
| Shell / 主进程文案 | 734 / 742 条，**99%** |
| 动态文案（`i18n/dynamic`） | 49 / 49 条，**100%** |
| Statsig 特性文案 | 65 条 |

剩余未译的是新版 Claude 才出现、翻译包尚未覆盖的 key，会自动回退英文，等你反馈后补齐。

## 快速使用

**前置条件**：Windows 10/11、[Python 3](https://www.python.org/downloads/)（安装时勾选 Add to PATH）、从 Microsoft Store 安装的 Claude。

1. 下载本仓库（Code → Download ZIP，或 `git clone`）
2. 双击 **`install.bat`**（会自动请求管理员权限）
3. 重启 Claude Code

脚本会从 [Releases](../../releases) 自动取翻译包 `resources-zh-CN.zip`。如果你的网络连 GitHub API 不通，手动下载该 zip 放到 `install.bat` 同目录，即可完全离线安装。

**卸载 / 还原英文**

```bash
install.bat --uninstall
```

会按备份逐文件还原，并把 `app\resources` 的所有权交还 `TrustedInstaller`。

## 它做了什么

1. `Get-AppxPackage` 定位 Claude 安装目录（普通权限即可，不需要枚举受保护的 `WindowsApps`）
2. 以官方 `en-US.json` 为底，叠加翻译包与补充译文，生成目标 `zh-CN.json` —— 所以 Claude 更新出新 key 也不会报错，只是那些条目回退英文
3. 备份将被改动的文件（`%LOCALAPPDATA%\claude-code-zh-cn\backup`），写 `manifest.json` 供一键还原
4. `takeown` + `icacls` 用 **SID**（Administrators + 当前用户）拿写入权限，不依赖默认禁用的内置 Administrator 账户
5. 部署 6 个文件：`ion-dist/i18n/zh-CN.json`、`zh-CN.overrides.json`、`dynamic/zh-CN.json`、`statsig/zh-CN.json`，以及主进程用的 `zh-CN.json`、`zh-CN.overrides.json`
6. 给 JS 打三处安全的字符串字面量补丁，每个改动文件先跑 `node --check`，不通过就自动回滚该文件：
   - 语言白名单加入 `zh-CN`
   - 语言名称表加入 `Chinese (China) / 简体中文 (中国)`
   - `localeChoice:null` → `localeChoice:"zh-CN"`（不钉住会被系统或账号语言顶回英文）
7. 把 `Claude-3p/config.json` 的 `locale` / `language` 设为 `zh-CN`

**没有"硬编码文本替换"这一步。** 早期版本会把 JS 源码里的 `Models` / `Extensions` / `tokens` 之类标识符一并翻译，破坏 `\p{Default_Ignorable_Code_Point}`、`Script_Extensions` 正则和 GitHub URL，导致整页白屏、设置页报 `1FV71M4`、`/new` 报 `1EUWK6G`。只保留 i18n 部署 + 语言开关，界面同样全中文且不会崩。

## 常见问题

- **提示未找到 Claude**：确认装的是 Microsoft Store 版；或手动指定 `install.bat --dir "C:\Program Files\WindowsApps\Claude_x.x.x.x_x64__pzs8sxrjxfjjc"`。
- **Claude 自动更新后变回英文**：正常，更新会覆盖汉化文件，重跑 `install.bat` 即可。
- **Store 更新报"包已损坏 / 修复失败"**：先 `install.bat --uninstall`（会把属主还给 `TrustedInstaller`），更新完再重装汉化。
- **想先看不动文件地了解状况**：`install.bat --check` 只诊断，不改动任何东西。

## 贡献翻译

翻译文本随 **Release 附件** `resources-zh-CN.zip` 分发，不进仓库。zip 内 6 个文件按 key（官方 i18n 的哈希）组织：

| 文件 | 说明 |
|------|------|
| `frontend-pack.json` / `frontend-extra.json` | 主界面；pack 为基础翻译，extra 为补充 |
| `shell-pack.json` / `shell-extra.json` | Shell / 主进程文案 |
| `dynamic-extra.json` | 动态下发文案 |
| `statsig-pack.json` | Statsig 特性文案 |

想补翻译：下载 zip，对照 Claude 安装目录里的 `ion-dist/i18n/en-US.json` 找出仍是英文的 key，把改好的文件发 issue 或 PR（附上 diff 就够，不用整包）。

## 许可与免责

- 本项目采用 MIT 许可，见 [LICENSE](LICENSE)，授权范围是安装脚本本身。
- 与 Anthropic 官方无关联。仓库与 Release 里都不含账号、密钥或个人路径；脚本只写本机 Claude 安装目录和你的 `AppData`。
- 汉化文本对应 Claude 官方界面字符串，请仅在个人使用范围内自行分发。

## 致谢

- [claude-desktop-zh-cn](https://github.com/xixu-me/Claude-Desktop-ZH-CN) — 基础前端翻译
