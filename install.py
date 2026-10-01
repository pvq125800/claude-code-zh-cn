"""
Claude Code 桌面版中文汉化 —— 一键安装/卸载
用法:
  python install.py              安装汉化
  python install.py --uninstall  还原英文
  python install.py --check      只诊断, 不改动

翻译文本不随仓库分发, 由本脚本自动从 GitHub Release 获取;
也可以把 resources-zh-CN.zip 放到本脚本同目录, 离线使用。
"""
import glob, json, os, shutil, subprocess, sys, tempfile, zipfile, urllib.request, urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(SCRIPT_DIR, "resources")
WORK_DIR = os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "claude-code-zh-cn")
BACKUP_DIR = os.path.join(WORK_DIR, "backup")
STAGING_DIR = os.path.join(WORK_DIR, "staging")
MANIFEST = os.path.join(WORK_DIR, "manifest.json")
CONFIG = os.path.expanduser(r"~\AppData\Local\Claude-3p\config.json")

RELEASE_REPO = "pvq125800/claude-code-zh-cn"
RELEASE_ZIP = "resources-zh-CN.zip"
RESOURCE_FILES = (
    "frontend-pack.json", "frontend-extra.json",
    "shell-pack.json", "shell-extra.json",
    "dynamic-extra.json", "statsig-pack.json",
)

LANG_LIST_OLD = '"en-US","de-DE","fr-FR","ko-KR","ja-JP","es-419","es-ES","it-IT","hi-IN","pt-BR","id-ID"'
LANG_LIST_NEW = LANG_LIST_OLD + ',"zh-CN"'
LOC_NAMES_OLD = '"id-ID":{name:"Indonesian (Indonesia)",localName:"Indonesia (Indonesia)"}'
LOC_NAMES_NEW = (
    LOC_NAMES_OLD
    + ',"zh-CN":{name:"Chinese (China)",localName:"\\u7b80\\u4f53\\u4e2d\\u6587 (\\u4e2d\\u56fd)"}'
)

# (staging 相对路径, 安装目录相对路径)
I18N_MAP = [
    ("ion-dist/i18n/zh-CN.json", "ion-dist/i18n/zh-CN.json"),
    ("ion-dist/i18n/zh-CN.overrides.json", "ion-dist/i18n/zh-CN.overrides.json"),
    ("ion-dist/i18n/dynamic/zh-CN.json", "ion-dist/i18n/dynamic/zh-CN.json"),
    ("ion-dist/i18n/statsig/zh-CN.json", "ion-dist/i18n/statsig/zh-CN.json"),
    ("shell/zh-CN.json", "zh-CN.json"),
    ("shell/zh-CN.overrides.json", "zh-CN.overrides.json"),
]


def log(msg):
    print(msg, flush=True)


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def run_ps(script, timeout=90):
    r = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                       capture_output=True, text=True, timeout=timeout)
    return (r.stdout or "").strip()


# ---------------------------------------------------------------- 资源获取
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
    req = urllib.request.Request(api, headers={"User-Agent": "claude-code-zh-cn",
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        info = json.load(resp)
    asset = next((a for a in info.get("assets", []) if a.get("name", "").endswith(".zip")), None)
    if not asset:
        raise RuntimeError(f"{RELEASE_REPO} 的最新 Release 里没有 zip 附件")
    url = asset["browser_download_url"]
    if not url.startswith("https://"):
        raise RuntimeError(f"下载地址不是 https: {url}")
    log(f"  下载 {info.get('tag_name', '?')} / {asset['name']} ({int(asset['size']) // 1024}KB)")
    with urllib.request.urlopen(url, timeout=300) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)


def ensure_resources():
    if resources_ready():
        return
    log("获取翻译包...")
    local_zip = os.path.join(SCRIPT_DIR, RELEASE_ZIP)
    try:
        if os.path.isfile(local_zip):
            log(f"  使用本地翻译包: {RELEASE_ZIP}")
            extract_resource_zip(local_zip)
        else:
            tmp = os.path.join(tempfile.gettempdir(), RELEASE_ZIP)
            download_release_zip(tmp)
            extract_resource_zip(tmp)
    except (urllib.error.URLError, RuntimeError, zipfile.BadZipFile, OSError) as e:
        log(f"[错误] 翻译包获取失败: {e}")
        log("  请手动下载 zip 并放到本脚本同目录后重新运行:")
        log(f"  https://github.com/{RELEASE_REPO}/releases/latest")
        sys.exit(1)
    missing = [n for n in RESOURCE_FILES if not os.path.isfile(os.path.join(RESOURCES_DIR, n))]
    if missing:
        log(f"[错误] 翻译包缺少文件: {', '.join(missing)}")
        sys.exit(1)
    log("  翻译包就绪\n")


# ---------------------------------------------------------------- 定位安装目录
def find_package(cli_dir=None):
    if cli_dir:
        return cli_dir

    loc = run_ps("$p = Get-AppxPackage -Name '*Claude*' | Sort-Object Version -Descending | "
                 "Select-Object -First 1; if ($p) { $p.InstallLocation }")
    if loc and os.path.isdir(loc):
        return loc

    p = run_ps("Get-Process claude,Claude-3p -ErrorAction SilentlyContinue | "
               "Select-Object -First 1 -ExpandProperty Path", timeout=60)
    if p and os.path.isfile(p):
        d = os.path.dirname(os.path.dirname(p))
        if os.path.isdir(d):
            return d

    cands = glob.glob(r"C:\Program Files\WindowsApps\Claude_*_x64__pzs8sxrjxfjjc")
    if cands:
        cands.sort(key=os.path.getmtime, reverse=True)
        return cands[0]
    return None


def res_dir(pkg):
    return os.path.join(pkg, "app", "resources")


def is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def require_admin():
    if is_admin():
        return
    log("[错误] 需要管理员权限。请右键 install.bat -> 以管理员身份运行")
    sys.exit(1)


def close_claude():
    n = run_ps("Get-Process claude,Claude-3p,cowork-svc -ErrorAction SilentlyContinue | "
               "Stop-Process -Force; Start-Sleep -Milliseconds 800; "
               "(Get-Process claude,Claude-3p,cowork-svc -ErrorAction SilentlyContinue | "
               "Measure-Object).Count", timeout=120)
    log(f"  已关闭 Claude, 剩余进程: {n}")


def grant_acl(rd):
    sid = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"],
                         capture_output=True, text=True, timeout=30).stdout.strip().strip('"').split('","')[-1]
    grants = ['"*S-1-5-32-544:(OI)(CI)(F)"']
    if sid:
        grants.append(f'"*{sid}:(OI)(CI)(F)"')
    log("  取得所有权 (takeown) ...")
    subprocess.run(f'takeown /F "{rd}" /A /R /D Y >nul 2>&1', shell=True, timeout=1800)
    log("  授权 (Administrators + 当前用户) ...")
    subprocess.run(f'icacls "{rd}" /grant {" ".join(grants)} /T /Q >nul 2>&1', shell=True, timeout=1800)


def restore_owner(rd):
    log("  把所有权交还 TrustedInstaller (让 Store 能正常更新) ...")
    subprocess.run(f'icacls "{rd}" /setowner "NT SERVICE\\TrustedInstaller" /T /Q >nul 2>&1',
                   shell=True, timeout=1800)


# ---------------------------------------------------------------- 生成翻译
def merge(base_en, *layers):
    out = dict(base_en)
    for layer in layers:
        for k, v in (layer or {}).items():
            if isinstance(v, str) and v.strip():
                out[k] = v
    return out


def zh_count(merged, en):
    return sum(1 for k, v in en.items() if merged.get(k, v) != v)


def build_translations(rd):
    fe_en = read_json(os.path.join(rd, "ion-dist", "i18n", "en-US.json"), {})
    dyn_en = read_json(os.path.join(rd, "ion-dist", "i18n", "dynamic", "en-US.json"), {})
    sh_en = read_json(os.path.join(rd, "en-US.json"), {})
    if not fe_en:
        log(f"[错误] 读不到官方翻译底稿: {os.path.join(rd, 'ion-dist', 'i18n', 'en-US.json')}")
        sys.exit(1)

    def res(name):
        return read_json(os.path.join(RESOURCES_DIR, name), {})

    fe = merge(fe_en, res("frontend-pack.json"), res("frontend-extra.json"))
    dyn = merge(dyn_en, res("dynamic-extra.json"))
    sh = merge(sh_en, res("shell-pack.json"), res("shell-extra.json"))
    sig = res("statsig-pack.json")

    shutil.rmtree(STAGING_DIR, ignore_errors=True)
    write_json(os.path.join(STAGING_DIR, "ion-dist/i18n/zh-CN.json"), fe)
    write_json(os.path.join(STAGING_DIR, "ion-dist/i18n/zh-CN.overrides.json"), {})
    write_json(os.path.join(STAGING_DIR, "ion-dist/i18n/dynamic/zh-CN.json"), dyn)
    write_json(os.path.join(STAGING_DIR, "ion-dist/i18n/statsig/zh-CN.json"), sig)
    write_json(os.path.join(STAGING_DIR, "shell/zh-CN.json"), sh)
    write_json(os.path.join(STAGING_DIR, "shell/zh-CN.overrides.json"), {})

    log(f"  前端界面 : {zh_count(fe, fe_en)}/{len(fe_en)} 已译 "
        f"({zh_count(fe, fe_en) * 100 // max(1, len(fe_en))}%)")
    log(f"  动态文案 : {zh_count(dyn, dyn_en)}/{len(dyn_en)}")
    log(f"  Shell    : {zh_count(sh, sh_en)}/{len(sh_en)}")
    log(f"  Statsig  : {len(sig)} 条")
    return {"fe": zh_count(fe, fe_en), "fe_total": len(fe_en)}


# ---------------------------------------------------------------- JS 补丁
def node_check(text):
    if not shutil.which("node"):
        return None
    tmp = os.path.join(tempfile.gettempdir(), "_claude_zh_syntax.mjs")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        return subprocess.run(["node", "--check", tmp], capture_output=True, timeout=120).returncode == 0
    except Exception:
        return None
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def patch_js(rd, manifest):
    """只做三处安全的字符串字面量补丁, 不翻译 JS 标识符。"""
    assets = os.path.join(rd, "ion-dist", "assets", "v1")
    if not os.path.isdir(assets):
        log(f"  [跳过] 找不到 {assets}")
        return 0, 0, 0
    changed = hits = rolled = 0
    for js in sorted(glob.glob(os.path.join(assets, "*.js"))):
        try:
            with open(js, encoding="utf-8") as f:
                orig = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        text, n = orig, 0
        if "localeChoice:null" in text:                      # 不钉住就会被系统语言顶回 en-US
            n += text.count("localeChoice:null")
            text = text.replace("localeChoice:null", 'localeChoice:"zh-CN"')
        if LANG_LIST_OLD in text and LANG_LIST_NEW not in text:  # NEW 以 OLD 开头, 不判就会重复追加
            n += text.count(LANG_LIST_OLD)
            text = text.replace(LANG_LIST_OLD, LANG_LIST_NEW)
        if LOC_NAMES_OLD in text and LOC_NAMES_NEW not in text:
            text = text.replace(LOC_NAMES_OLD, LOC_NAMES_NEW)
            n += 1
        if text == orig:
            continue
        if node_check(orig) is True and node_check(text) is False:
            log(f"  [回滚] 补丁后语法校验不通过: {os.path.basename(js)}")
            rolled += 1
            continue
        rel = os.path.relpath(js, rd).replace("\\", "/")
        bak = os.path.join(BACKUP_DIR, rel)
        os.makedirs(os.path.dirname(bak), exist_ok=True)
        if not os.path.exists(bak):
            shutil.copy2(js, bak)
            manifest["modified"].append({"path": js, "backup": bak})
        with open(js, "w", encoding="utf-8") as f:
            f.write(text)
        changed += 1
        hits += n
    return changed, hits, rolled


# ---------------------------------------------------------------- 安装 / 卸载
def load_manifest(pkg):
    m = read_json(MANIFEST, {}) or {}
    m.setdefault("package", pkg)
    m.setdefault("version", os.path.basename(pkg))
    m.setdefault("modified", [])
    m.setdefault("added", [])
    m.setdefault("config_backup", None)
    return m


def install(pkg):
    rd = res_dir(pkg)
    require_admin()
    log(f"安装目录: {pkg}\n")

    log("[1/4] 生成翻译文件...")
    stats = build_translations(rd)

    log("\n[2/4] 部署 (管理员权限)...")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    close_claude()
    grant_acl(rd)
    manifest = load_manifest(pkg)

    for src_rel, dst_rel in I18N_MAP:
        s = os.path.join(STAGING_DIR, src_rel.replace("/", os.sep))
        d = os.path.join(rd, dst_rel.replace("/", os.sep))
        if not os.path.exists(s):
            continue
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if os.path.exists(d):
            bak = os.path.join(BACKUP_DIR, dst_rel)
            os.makedirs(os.path.dirname(bak), exist_ok=True)
            if not os.path.exists(bak):
                shutil.copy2(d, bak)
                manifest["modified"].append({"path": d, "backup": bak})
        elif d not in [x["path"] for x in manifest["added"]]:
            manifest["added"].append({"path": d})
        shutil.copy2(s, d)
    log("  翻译文件已部署")

    log("  语言补丁 (白名单 + 名称表 + localeChoice) ...")
    changed, hits, rolled = patch_js(rd, manifest)
    log(f"    改动 {changed} 个 JS, {hits} 处补丁, {rolled} 个因语法校验回滚")

    log("\n[3/4] 更新配置...")
    if os.path.exists(CONFIG):
        if not manifest["config_backup"]:
            cb = os.path.join(BACKUP_DIR, "config.json")
            os.makedirs(BACKUP_DIR, exist_ok=True)
            shutil.copy2(CONFIG, cb)
            manifest["config_backup"] = cb
        cfg = read_json(CONFIG, {})
        cfg["locale"] = "zh-CN"
        cfg["language"] = "zh-CN"
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=1, ensure_ascii=False)
        log("  locale/language -> zh-CN")
    else:
        log("  config.json 尚不存在, 跳过 (首次启动 Claude 后再运行一次)")

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)

    log("\n[4/4] 验证...")
    ok = verify(pkg)
    log("")
    if ok:
        log("汉化完成! 请重启 Claude Code 桌面版。")
        log(f"原始文件备份在 {BACKUP_DIR}, 随时可用 --uninstall 还原。")
    else:
        log("部分项目缺失, 请检查上方输出。")
    return 0 if ok else 1


def uninstall(pkg):
    require_admin()
    rd = res_dir(pkg)
    manifest = read_json(MANIFEST, {}) or {}
    log("关闭 Claude ...")
    close_claude()
    grant_acl(rd)

    n = 0
    for m in manifest.get("modified", []):
        bak, dst = m.get("backup"), m.get("path")
        if bak and dst and os.path.exists(bak):
            try:
                shutil.copy2(bak, dst)
                n += 1
            except OSError as e:
                log(f"  [失败] {dst}: {e}")
    log(f"  还原 {n} 个被修改的文件")

    removed = 0
    for m in manifest.get("added", []):
        p = m.get("path")
        if p and os.path.exists(p):
            try:
                os.remove(p)
                removed += 1
            except OSError:
                pass
    for rel in [t for _, t in I18N_MAP] + ["ion-dist/i18n/statsig/zh-CN.json"]:
        p = os.path.join(rd, rel.replace("/", os.sep))
        if os.path.exists(p):
            try:
                os.remove(p)
                removed += 1
            except OSError:
                pass
    log(f"  删除 {removed} 个汉化文件")

    cb = manifest.get("config_backup")
    if cb and os.path.exists(cb) and os.path.exists(CONFIG):
        shutil.copy2(cb, CONFIG)
        log("  config.json 已还原")
    elif os.path.exists(CONFIG):
        cfg = read_json(CONFIG, {})
        cfg["locale"] = "en-US"
        cfg["language"] = "en-US"
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=1, ensure_ascii=False)
        log("  config locale -> en-US")

    restore_owner(rd)
    if os.path.exists(MANIFEST):
        os.remove(MANIFEST)
    log("已还原英文原版, 重启 Claude 生效。")
    return 0


def verify(pkg):
    rd = res_dir(pkg)
    ok = True
    for rel in ["ion-dist/i18n/zh-CN.json", "ion-dist/i18n/dynamic/zh-CN.json",
                "ion-dist/i18n/zh-CN.overrides.json", "zh-CN.json"]:
        p = os.path.join(rd, rel.replace("/", os.sep))
        if os.path.exists(p):
            log(f"  {rel}: {os.path.getsize(p) // 1024} KB")
        else:
            log(f"  {rel}: 缺失")
            ok = False
    patched = named = pinned = 0
    for js in glob.glob(os.path.join(rd, "ion-dist", "assets", "v1", "*.js")):
        try:
            with open(js, encoding="utf-8") as f:
                t = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        patched += LANG_LIST_NEW in t
        named += '"zh-CN":{name:"Chinese (China)"' in t
        pinned += 'localeChoice:"zh-CN"' in t
    log(f"  语言白名单: {patched} 个文件 / 名称表: {named} / localeChoice 钉住: {pinned}")
    ok = ok and patched > 0
    if os.path.exists(CONFIG):
        log(f"  config.json locale = {read_json(CONFIG, {}).get('locale')}")
    return ok


def check(pkg):
    rd = res_dir(pkg)
    log(f"安装目录: {pkg}")
    log(f"resources: {rd}  存在={os.path.isdir(rd)}")
    log(f"管理员权限: {is_admin()}")
    log(f"node 可用于语法校验: {bool(shutil.which('node'))}")
    for rel in ["ion-dist/i18n/en-US.json", "ion-dist/i18n/dynamic/en-US.json", "en-US.json"]:
        p = os.path.join(rd, rel.replace("/", os.sep))
        state = f"存在 {os.path.getsize(p)}B" if os.path.exists(p) else "缺失"
        log(f"  {rel}: {state}")
    return verify(pkg)


def main():
    args = sys.argv[1:]
    log("=" * 46)
    log("  Claude Code 桌面版 中文汉化")
    log("=" * 46)

    cli_dir = None
    if "--dir" in args:
        cli_dir = args[args.index("--dir") + 1]
    pkg = find_package(cli_dir)
    if not pkg:
        log("[错误] 未找到 Claude Code 桌面版")
        log("  请确认已从 Microsoft Store 安装 Claude, 或用 --dir 指定安装目录")
        return 1

    log(f"版本: {os.path.basename(pkg)}\n")
    if "--check" in args:
        return 0 if check(pkg) else 1
    ensure_resources()
    if "--uninstall" in args:
        return uninstall(pkg)
    return install(pkg)


if __name__ == "__main__":
    sys.exit(main())
