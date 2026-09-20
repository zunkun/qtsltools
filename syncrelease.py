#!/usr/bin/env python3
r"""
syncrelease.py —— 把 assets/ 同步到 GitHub Release（tag: database）

仓库: https://github.com/zunkun/qtsltools
Release「数据仓库」作为数据仓库使用，只维护以下三类文件：
  1. update.json      —— 每次执行都强制更新（clobber 覆盖上传）
  2. 最新 APK         —— update.json 的 apk.name，线上已有则跳过
  3. 数据包 ZIP       —— update.json 的 dataPackList 里引用的所有 zip，
                         线上已有同版本则跳过；旧版本 zip 保留不删

其他线上资源（about.json、privacy*.json、favicon.ico 等）一律不动。
同名但文件大小不一致的资源视为异常，自动 clobber 重新上传。

用法:
  python syncrelease.py                # 正式同步
  python syncrelease.py --dry-run      # 只打印计划，不做任何改动
  python syncrelease.py --prune-old    # 额外删除线上“本地已不存在”的旧 apk/zip
  python syncrelease.py --force        # 同名资源也强制重新上传
  python syncrelease.py --token xxxxx  # 用 GitHub Token 代替 gh auth login

前置条件（二选一）:
  A. gh auth login  （gh 装好后新开一个终端，或直接用完整路径:
     & "C:\Program Files\GitHub CLI\gh.exe" auth login ）
  B. 设置环境变量 GH_TOKEN / GITHUB_TOKEN，或运行时传 --token
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# ===================== 配置 =====================
SCRIPT_PATH = Path(__file__).resolve()
ASSET_DIR = SCRIPT_PATH.parent / "assets"
UPDATE_JSON = ASSET_DIR / "update.json"

REPO = "zunkun/qtsltools"
TAG = "database"
RELEASE_TITLE = "数据仓库"
RELEASE_NOTES = "数据仓库：update.json / 最新APK / 数据包zip"

# gh.exe 常见安装位置（PATH 未刷新时兜底）
GH_CANDIDATES = [
    r"C:\Program Files\GitHub CLI\gh.exe",
    r"C:\Program Files (x86)\GitHub CLI\gh.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\GitHub CLI\gh.exe"),
]
# ================================================

try:  # Windows 控制台输出 emoji/中文
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def find_gh() -> str:
    """定位 gh.exe：优先 PATH，其次常见安装目录。"""
    found = []
    try:
        p = subprocess.run(["where", "gh"], capture_output=True)
        found = p.stdout.decode("utf-8", errors="replace").strip().splitlines()
    except Exception:
        found = []
    if found:
        return found[0].strip()
    for cand in GH_CANDIDATES:
        if Path(cand).is_file():
            return cand
    # 非 Windows / 其他位置
    which = 1
    try:
        which = subprocess.run(
            ["gh", "--version"], capture_output=True
        ).returncode
    except Exception:
        which = 1
    if which == 0:
        return "gh"
    print("❌ 找不到 gh.exe，请确认 GitHub CLI 已安装，或将其加入 PATH。")
    sys.exit(1)


def run_gh(gh: str, args: list, token: str = None):
    """执行 gh 子命令。返回 (returncode, stdout, stderr)。"""
    env = os.environ.copy()
    if token:
        env["GH_TOKEN"] = token
    try:
        p = subprocess.run(
            [gh] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        print(f"❌ 无法执行 gh: {gh}")
        sys.exit(1)


def check_auth(gh: str, token: str = None) -> bool:
    rc, out, err = run_gh(gh, ["auth", "status"], token)
    return rc == 0


def get_release_assets(gh: str, token: str = None):
    """返回 (release存在?, {资源名: 资源dict})。"""
    rc, out, err = run_gh(
        gh, ["release", "view", TAG, "-R", REPO, "--json", "assets"], token
    )
    if rc != 0:
        if "not found" in (err or "").lower():
            return False, {}
        print(f"❌ 查询 Release 失败:\n{err or out}")
        sys.exit(1)
    assets = json.loads(out).get("assets", [])
    return True, {a["name"]: a for a in assets}


def create_release(gh: str, token: str = None):
    print(f"🆕 Release(tag={TAG}) 不存在，正在创建...")
    rc, out, err = run_gh(
        gh,
        [
            "release", "create", TAG, "-R", REPO,
            "--title", RELEASE_TITLE,
            "--notes", RELEASE_NOTES,
        ],
        token,
    )
    if rc != 0:
        print(f"❌ 创建 Release 失败:\n{err or out}")
        sys.exit(1)


def upload_asset(gh: str, file_path: Path, token: str = None, clobber=False):
    args = ["release", "upload", TAG, str(file_path), "-R", REPO]
    if clobber:
        args.append("--clobber")
    rc, out, err = run_gh(gh, args, token)
    if rc != 0:
        print(f"❌ 上传 {file_path.name} 失败:\n{err or out}")
        sys.exit(1)


def delete_asset(gh: str, name: str, token: str = None):
    rc, out, err = run_gh(
        gh, ["release", "delete-asset", TAG, name, "-R", REPO, "--yes"], token
    )
    if rc != 0:
        print(f"❌ 删除线上资源 {name} 失败:\n{err or out}")
        sys.exit(1)


def load_sync_plan():
    """从 update.json 解析需要保证线上的文件清单。"""
    if not UPDATE_JSON.is_file():
        print(f"❌ 找不到 {UPDATE_JSON}，请先运行 hashfile.py 生成。")
        sys.exit(1)
    cfg = json.loads(UPDATE_JSON.read_text(encoding="utf-8"))
    plan = {"update.json": UPDATE_JSON}
    apk_name = (cfg.get("apk") or {}).get("name")
    if apk_name:
        plan[apk_name] = ASSET_DIR / apk_name
    for item in cfg.get("dataPackList") or []:
        name = item.get("name")
        if name:
            plan[name] = ASSET_DIR / name
    return plan


def warn_unreferenced(plan_keys):
    """本地存在但 update.json 未引用的 apk/zip，提示先跑 hashfile.py。"""
    unreferenced = [
        p.name
        for p in ASSET_DIR.iterdir()
        if p.is_file()
        and (p.suffix in (".apk", ".zip"))
        and p.name not in plan_keys
    ]
    for name in unreferenced:
        print(f"⚠️ 本地 {name} 未被 update.json 引用，本次不会上传（先运行 hashfile.py 刷新清单）")


def main():
    parser = argparse.ArgumentParser(description="同步 assets 到 GitHub Release(database)")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不执行任何改动")
    parser.add_argument("--force", action="store_true", help="同名资源也强制重新上传")
    parser.add_argument("--prune-old", action="store_true",
                        help="删除线上 apk/zip 中本地已不存在的旧版本（默认保留）")
    parser.add_argument("--token", default=None, help="GitHub Token（免 gh auth login）")
    args = parser.parse_args()

    gh = find_gh()
    print(f"🔧 gh: {gh}")

    if not check_auth(gh, args.token):
        print("❌ GitHub 未登录。请任选其一：")
        print('   1) 新开终端执行: gh auth login   （若提示找不到 gh，')
        print('      用完整路径: & "C:\\Program Files\\GitHub CLI\\gh.exe" auth login ）')
        print("   2) 或设置环境变量 GH_TOKEN / 运行时加 --token <token>")
        sys.exit(1)
    print("✅ GitHub 已登录")

    plan = load_sync_plan()
    warn_unreferenced(set(plan.keys()))

    # 校验本地文件都在
    missing_local = [n for n, p in plan.items() if not p.is_file()]
    if missing_local:
        print(f"❌ update.json 引用的文件在 assets/ 中缺失: {missing_local}")
        sys.exit(1)

    exists, online = get_release_assets(gh, args.token)
    if not exists and not args.dry_run:
        create_release(gh, args.token)
        _, online = get_release_assets(gh, args.token)

    print(f"\n📋 线上现有资源 {len(online)} 个: {sorted(online.keys())}")
    print("──────────────────────────────────────")

    actions = []  # (动作, 文件名)
    for name, local_path in plan.items():
        if name == "update.json":
            # update.json 每次都强制覆盖更新
            actions.append(("覆盖", name))
            continue
        online_size = online[name]["size"] if name in online else None
        if name in online:
            if online_size != local_path.stat().st_size:
                actions.append(("覆盖", name))  # 同名不同内容，视为异常
            elif args.force:
                actions.append(("覆盖", name))
            else:
                actions.append(("跳过(已有)", name))
        else:
            actions.append(("上传", name))

    if args.prune_old:
        keep = set(plan.keys())
        for name in online:
            if name in keep:
                continue
            if name == "update.json":
                continue
            if name.endswith(".apk") or name.endswith(".zip"):
                actions.append(("删除旧版", name))

    # 打印计划
    for act, name in actions:
        print(f"  [{act}] {name}")
    if args.dry_run:
        print("\n🧪 dry-run 结束，未做任何改动。")
        return

    # 执行
    for act, name in actions:
        if act == "上传":
            print(f"⬆️  上传 {name} ...")
            upload_asset(gh, plan[name], args.token)
        elif act == "覆盖":
            print(f"♻️  覆盖上传 {name} ...")
            upload_asset(gh, plan[name], args.token, clobber=True)
        elif act == "删除旧版":
            print(f"🗑️  删除线上旧资源 {name} ...")
            delete_asset(gh, name, args.token)

    print("\n✅ 同步完成！查看: https://github.com/zunkun/qtsltools/releases/tag/database")


if __name__ == "__main__":
    main()
