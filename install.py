"""
Claude Code 桌面版中文汉化安装包 (独立版)
用法: python3 install.py [--uninstall]

翻译文本不随仓库分发, 由 install.py 自动从 GitHub Release 获取;
也可以把 resources-zh-CN.zip 放到本脚本同目录, 离线使用。
"""
import json, os, sys, glob, subprocess, tempfile, shutil, zipfile, urllib.request, urllib.error
from pathlib import Path

# ============ 配置 ============
WINDOWSAPPS = r"C:\Program Files\WindowsApps"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(SCRIPT_DIR, "resources")
TEMP_ROOT = os.path.join(tempfile.gettempdir(), "claude-zh-cn-patch")
CLAUDE3P_CONFIG = os.path.expanduser(r"~\AppData\Local\Claude-3p\config.json")

RELEASE_REPO = "pvq125800/claude-code-zh-cn"
RELEASE_ZIP = "resources-zh-CN.zip"
RESOURCE_FILES = (
    "frontend-zh-CN.json",
    "shell-zh-CN.json",
    "statsig-zh-CN.json",
    "hardcoded-zh-CN.json",
)

LANG_PATTERN = '"en-US","de-DE","fr-FR","ko-KR","ja-JP","es-419","es-ES","it-IT","hi-IN","pt-BR","id-ID"'
LANG_REPLACEMENT = '"en-US","de-DE","fr-FR","ko-KR","ja-JP","es-419","es-ES","it-IT","hi-IN","pt-BR","id-ID","zh-CN"'


def find_claude_dir():
    """扫描 WindowsApps 找到最新版 Claude 安装目录"""
    candidates = glob.glob(os.path.join(WINDOWSAPPS, "Claude_*_x64__pzs8sxrjxfjjc"))
    if not candidates:
        print("[错误] 未找到 Claude Code 桌面版")
        print(f"  搜索: {WINDOWSAPPS}\\Claude_*")
        print("  请确认已从 Microsoft Store 安装 Claude")
        sys.exit(1)
    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[0]


def resources_ready():
    return all(os.path.isfile(os.path.join(RESOURCES_DIR, n)) for n in RESOURCE_FILES)


def extract_resource_zip(zip_path):
    os.makedirs(RESOURCES_DIR, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            base = os.path.basename(name)
            if base in RESOURCE_FILES:
                with zf.open(name) as src, open(os.path.join(RESOURCES_DIR, base), "wb") as dst:
                    shutil.copyfileobj(src, dst)


def download_release_zip(dest):
    api = f"https://api.github.com/repos/{RELEASE_REPO}/releases/latest"
    req = urllib.request.Request(api, headers={"User-Agent": "claude-code-zh-cn", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        info = json.load(resp)
    asset = next((a for a in info.get("assets", []) if a.get("name", "").endswith(".zip")), None)
    if not asset:
        raise RuntimeError(f"{RELEASE_REPO} 的最新 Release 里没有 zip 附件")
    url = asset["browser_download_url"]
    if not url.startswith("https://"):
        raise RuntimeError(f"下载地址不是 https: {url}")
    print(f"  下载 {info.get('tag_name', '?')} / {asset['name']} ({int(asset['size']) // 1024}KB)")
    with urllib.request.urlopen(url, timeout=180) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)


def ensure_resources():
    """翻译文本不在仓库里, 缺失时先找同目录 zip, 再从 GitHub Release 下载"""
    if resources_ready():
        return
    print("[0/4] 获取翻译包...")
    local_zip = os.path.join(SCRIPT_DIR, RELEASE_ZIP)
    try:
        if os.path.isfile(local_zip):
            print(f"  使用本地翻译包: {os.path.basename(local_zip)}")
            extract_resource_zip(local_zip)
        else:
            tmp_zip = os.path.join(tempfile.gettempdir(), RELEASE_ZIP)
            download_release_zip(tmp_zip)
            extract_resource_zip(tmp_zip)
    except (urllib.error.URLError, RuntimeError, zipfile.BadZipFile, OSError) as e:
        print(f"[错误] 翻译包获取失败: {e}")
        print("  请手动下载, 然后把 zip 放到本脚本同目录后重新运行:")
        print(f"  https://github.com/{RELEASE_REPO}/releases/latest")
        sys.exit(1)
    missing = [n for n in RESOURCE_FILES if not os.path.isfile(os.path.join(RESOURCES_DIR, n))]
    if missing:
        print(f"[错误] 翻译包缺少文件: {', '.join(missing)}")
        sys.exit(1)
    print("  翻译包就绪\n")


def load_builtin_translations():
    """从内置资源加载翻译"""
    frontend = json.load(open(os.path.join(RESOURCES_DIR, "frontend-zh-CN.json"), encoding="utf-8"))
    shell = json.load(open(os.path.join(RESOURCES_DIR, "shell-zh-CN.json"), encoding="utf-8"))
    statsig = json.load(open(os.path.join(RESOURCES_DIR, "statsig-zh-CN.json"), encoding="utf-8"))
    hardcoded_path = os.path.join(RESOURCES_DIR, "hardcoded-zh-CN.json")
    hardcoded = json.load(open(hardcoded_path, encoding="utf-8")) if os.path.exists(hardcoded_path) else []
    return frontend, shell, statsig, hardcoded


def prepare_files(claude_dir):
    """合并内置翻译 + 补全新版 key，写入临时目录"""
    resources = os.path.join(claude_dir, "app", "resources")

    # 加载内置翻译
    frontend_zh, shell_zh, sig_zh, hardcoded_zh = load_builtin_translations()
    print(f"  内置翻译: 前端 {len(frontend_zh)} 条, Shell {len(shell_zh)} 条, 硬编码 {len(hardcoded_zh)} 条")

    # 读取新版英文 key，补全缺失
    en_fe_path = os.path.join(resources, "ion-dist", "i18n", "en-US.json")
    en_fe = json.load(open(en_fe_path, encoding="utf-8"))
    new_keys = set(en_fe.keys()) - set(frontend_zh.keys())
    for k in new_keys:
        frontend_zh[k] = en_fe[k]
    if new_keys:
        print(f"  新版新增: {len(new_keys)} 条 (回退英文)")
    print(f"  最终覆盖: {len(frontend_zh)}/{len(en_fe)} ({len(frontend_zh)*100//len(en_fe)}%)")

    # 写入临时目录
    fe_dir = os.path.join(TEMP_ROOT, "ion-dist", "i18n")
    sig_dir = os.path.join(fe_dir, "statsig")
    os.makedirs(sig_dir, exist_ok=True)

    for path, data in [
        (os.path.join(fe_dir, "zh-CN.json"), frontend_zh),
        (os.path.join(fe_dir, "zh-CN.overrides.json"), {}),
        (os.path.join(sig_dir, "zh-CN.json"), sig_zh),
        (os.path.join(TEMP_ROOT, "zh-CN.json"), shell_zh),
    ]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    for name, p in [("前端", os.path.join(fe_dir, "zh-CN.json")),
                     ("Shell", os.path.join(TEMP_ROOT, "zh-CN.json")),
                     ("Statsig", os.path.join(sig_dir, "zh-CN.json"))]:
        print(f"  {name}: {os.path.getsize(p)//1024}KB")


def find_js_with_langlist(resources):
    """找到包含语言白名单的 JS 文件"""
    assets_dir = os.path.join(resources, "ion-dist", "assets", "v1")
    if not os.path.isdir(assets_dir):
        return None
    for js_file in glob.glob(os.path.join(assets_dir, "*.js")):
        if js_file.endswith(".bak"):
            continue
        try:
            with open(js_file, "r", encoding="utf-8") as f:
                if LANG_PATTERN in f.read():
                    return js_file
        except Exception:
            continue
    return None


def deploy(claude_dir):
    """用管理员 PowerShell 获取权限 + Python 做文本替换"""
    resources = os.path.join(claude_dir, "app", "resources")

    # Step 1: 用 PowerShell 获取写入权限
    print("  获取文件权限...")
    ps_cmd = (
        f'takeown /F "{resources}" /A /R 2>&1 | Out-Null; '
        f'icacls "{resources}" /grant "Administrator:(OI)(CI)(F)" /T /Q 2>&1 | Out-Null'
    )
    ps_file = os.path.join(TEMP_ROOT, "_grant.ps1")
    with open(ps_file, "w", encoding="utf-8-sig") as f:
        f.write(f'$ErrorActionPreference = "Stop"\n{ps_cmd}')
    subprocess.run(
        ["powershell", "-Command",
         f"Start-Process powershell -Verb RunAs -Wait "
         f"-ArgumentList '-ExecutionPolicy Bypass -File {ps_file}'"],
        capture_output=True, timeout=120,
    )

    # Step 2: Python 做文件复制和 JS 补丁
    print("  部署翻译文件...")
    fe_src = os.path.join(TEMP_ROOT, "ion-dist", "i18n")
    fe_dst = os.path.join(resources, "ion-dist", "i18n")
    sig_src = os.path.join(fe_src, "statsig")
    sig_dst = os.path.join(fe_dst, "statsig")
    for s, d in [
        (os.path.join(fe_src, "zh-CN.json"), os.path.join(fe_dst, "zh-CN.json")),
        (os.path.join(fe_src, "zh-CN.overrides.json"), os.path.join(fe_dst, "zh-CN.overrides.json")),
        (os.path.join(sig_src, "zh-CN.json"), os.path.join(sig_dst, "zh-CN.json")),
        (os.path.join(TEMP_ROOT, "zh-CN.json"), os.path.join(resources, "zh-CN.json")),
    ]:
        shutil.copy2(s, d)

    # Step 3: 语言白名单补丁
    print("  语言白名单补丁...")
    js_with_langlist = find_js_with_langlist(resources)
    if js_with_langlist:
        with open(js_with_langlist, "r", encoding="utf-8") as f:
            content = f.read()
        if LANG_PATTERN in content:
            content = content.replace(LANG_PATTERN, LANG_REPLACEMENT)
            with open(js_with_langlist, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"    {os.path.basename(js_with_langlist)}: OK")

    # Step 4: 硬编码文本替换 —— 已禁用
    # 该步骤会把 JS 代码中的 Default/Extensions/tokens 等标识符一并翻译,
    # 导致 \p{Default_Ignorable_Code_Point} 等正则与 URL 被破坏,应用白屏崩溃。
    print("  硬编码替换: 已跳过 (会破坏 JS 代码)")


def update_config():
    """更新 config locale"""
    if not os.path.exists(CLAUDE3P_CONFIG):
        print("  config.json 不存在, 跳过")
        return
    with open(CLAUDE3P_CONFIG, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    cfg["locale"] = "zh-CN"
    cfg["language"] = "zh-CN"
    with open(CLAUDE3P_CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print("  locale -> zh-CN")


def uninstall(claude_dir):
    """卸载汉化"""
    resources = os.path.join(claude_dir, "app", "resources")
    targets = [
        f"$res\\ion-dist\\i18n\\zh-CN.json",
        f"$res\\ion-dist\\i18n\\zh-CN.overrides.json",
        f"$res\\ion-dist\\i18n\\statsig\\zh-CN.json",
        f"$res\\zh-CN.json",
    ]
    remove_lines = "\n".join(
        f'if (Test-Path "{t}") {{ Remove-Item "{t}" -Force; Write-Host "removed: {os.path.basename(t)}" }}'
        for t in targets
    )
    ps_script = f"""$ErrorActionPreference = 'Stop'
$res = '{resources}'
takeown /F $res /A /R 2>&1 | Out-Null
icacls $res /grant 'Administrator:(OI)(CI)(F)' /T /Q 2>&1 | Out-Null
{remove_lines}
"""
    ps_file = os.path.join(TEMP_ROOT, "_uninstall.ps1")
    os.makedirs(TEMP_ROOT, exist_ok=True)
    with open(ps_file, "w", encoding="utf-8-sig") as f:
        f.write(ps_script)
    subprocess.run(
        ["powershell", "-Command",
         f"Start-Process powershell -Verb RunAs -Wait "
         f"-ArgumentList '-ExecutionPolicy Bypass -File {ps_file}'"],
        capture_output=True, timeout=120,
    )
    if os.path.exists(CLAUDE3P_CONFIG):
        with open(CLAUDE3P_CONFIG, encoding="utf-8-sig") as f:
            cfg = json.load(f)
        cfg["locale"] = "en-US"
        with open(CLAUDE3P_CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)


def verify(claude_dir):
    """验证部署"""
    resources = os.path.join(claude_dir, "app", "resources")
    ok = True
    for name, p in [
        ("前端翻译", os.path.join(resources, "ion-dist", "i18n", "zh-CN.json")),
        ("Shell 翻译", os.path.join(resources, "zh-CN.json")),
    ]:
        if os.path.exists(p):
            print(f"  {name}: {os.path.getsize(p)//1024}KB")
        else:
            print(f"  {name}: MISSING!")
            ok = False

    # JS 补丁
    js_dir = os.path.join(resources, "ion-dist", "assets", "v1")
    has_zh = False
    if os.path.isdir(js_dir):
        for f in glob.glob(os.path.join(js_dir, "*.js")):
            if f.endswith(".bak"):
                continue
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    if '"zh-CN"' in fh.read():
                        has_zh = True
                        break
            except Exception:
                continue
    print(f"  JS 补丁: {'OK' if has_zh else 'MISSING'}")
    return ok and has_zh


def main():
    args = sys.argv[1:]
    do_uninstall = "--uninstall" in args

    print("=" * 50)
    print("Claude Code 桌面版 中文汉化")
    print("=" * 50)

    claude_dir = find_claude_dir()
    version = os.path.basename(claude_dir).split("_")[1]
    print(f"版本: {version}\n")

    if do_uninstall:
        print("[卸载]...")
        uninstall(claude_dir)
        print("\n完成! 请重启 Claude Code。")
        return

    ensure_resources()

    print("[1/4] 准备翻译文件...")
    prepare_files(claude_dir)

    print("\n[2/4] 部署翻译 + 语言白名单补丁 (管理员权限)...")
    deploy(claude_dir)

    print("\n[3/4] 更新配置...")
    update_config()

    print("\n[4/4] 验证...")
    print("=" * 50)
    if verify(claude_dir):
        print("汉化完成! 请重启 Claude Code 桌面版。")
    else:
        print("部分验证失败，请检查上方输出。")
    print("=" * 50)


if __name__ == "__main__":
    main()
