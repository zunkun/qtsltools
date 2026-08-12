#!/usr/bin/env python3
import shutil
import argparse
from pathlib import Path
import sys
import zipfile

# ========== 路径推导（此副本专属） ==========
SCRIPT_PATH = Path(__file__).resolve()
# 当前脚本 D:\workspace\qtsltools\syncdbfile.py
WORKSPACE_ROOT = SCRIPT_PATH.parent.parent  # D:\workspace
WEBAPI_BASE = WORKSPACE_ROOT / "qtsl" / "webapi"
sys.path.insert(0, str(WEBAPI_BASE))
# ===========================================

# ===================== 配置 =====================
DEFAULT_SQLITE = WEBAPI_BASE / "static" / "qtsl_core.sqlite"
SHARE_DIR = Path(r"D:\share")
CHECKSUM_NAME = "checksum_md5.txt"
ASSET_TARGET_ROOT = Path(r"D:\workspace\qtsltools\assets")
# =================================================

from scripts.sqlitedb.md5_hash import write_checksum


def create_zip(zip_path: Path, db_path: Path, ck_path: Path):
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(db_path, arcname=db_path.name)
        zf.write(ck_path, arcname=ck_path.name)
    print(f"🗜️  压缩包创建完成: {zip_path.resolve()}")


def sync_to_share(db_path: Path, ck_path: Path, target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_path, target_dir / db_path.name)
    shutil.copy2(ck_path, target_dir / ck_path.name)
    print(f"📦 {db_path.name} → {target_dir}")
    print(f"📦 {ck_path.name} → {target_dir}")


def run_sync(sqlite_file: Path, version: str):
    if not sqlite_file.exists():
        print(f"❌ 数据库文件不存在: {sqlite_file.resolve()}")
        sys.exit(1)

    ck_file = write_checksum(sqlite_file)
    if ck_file.name != CHECKSUM_NAME:
        new_ck_path = ck_file.with_name(CHECKSUM_NAME)
        shutil.move(ck_file, new_ck_path)
        ck_file = new_ck_path
    print(f"✅ MD5校验文件生成: {ck_file.resolve()}")

    # zip 和 sqlite 同目录 static
    zip_filename = f"data-v{version}.zip"
    zip_output_path = sqlite_file.parent / zip_filename
    create_zip(zip_output_path, sqlite_file, ck_file)

    # 复制zip到 qtsltools/assets，不存在qtsltools目录则跳过
    qtsltools_root = ASSET_TARGET_ROOT.parent
    if qtsltools_root.exists():
        ASSET_TARGET_ROOT.mkdir(exist_ok=True)
        shutil.copy2(zip_output_path, ASSET_TARGET_ROOT / zip_filename)
        print(f"📤 Zip包复制成功 → {ASSET_TARGET_ROOT / zip_filename}")
    else:
        print(f"⚠️ 目录不存在 {qtsltools_root}，跳过Zip复制操作")

    # 同步sqlite、md5文件到 D:\share
    sync_to_share(sqlite_file, ck_file, SHARE_DIR)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite数据库打包同步分发工具")
    parser.add_argument("--version", "-v", required=True, help="版本号，不可省略")
    parser.add_argument("db_file", nargs='?', default=None, help="(可选) SQLite数据库路径，不填使用默认文件")
    args = parser.parse_args()

    if args.db_file:
        target_db = Path(args.db_file)
    else:
        target_db = DEFAULT_SQLITE
        print(f"未指定数据库路径，使用默认库：{target_db.resolve()}")

    run_sync(target_db, args.version)
