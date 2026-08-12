#!/usr/bin/env python3
import hashlib
from pathlib import Path

# ===================== 配置 =====================
SCRIPT_PATH = Path(__file__).resolve()
ASSET_DIR = SCRIPT_PATH.parent / "assets"
OUTPUT_FILE = ASSET_DIR / "md5.txt"
# =================================================


def calc_md5(file_path: Path, chunk_size=65536) -> str:
    """计算文件md5"""
    md5_obj = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5_obj.update(chunk)
    return md5_obj.hexdigest()


def generate_assets_md5():
    ASSET_DIR.mkdir(exist_ok=True)
    # 匹配 zip + apk，仅当前目录，不递归子文件夹
    target_files = []
    target_files.extend(ASSET_DIR.glob("*.zip"))
    target_files.extend(ASSET_DIR.glob("*.apk"))
    # 文件名倒序排列
    target_files = sorted(target_files, key=lambda p: p.name, reverse=True)

    if not target_files:
        print(f"⚠️ {ASSET_DIR} 下未找到任何 *.zip / *.apk 文件")
        OUTPUT_FILE.write_text("", encoding="utf-8")
        return

    lines = []
    for f in target_files:
        md5_val = calc_md5(f)
        line = f"{f.name} {md5_val}"
        lines.append(line)
        print(line)

    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n✅ MD5清单已保存至：{OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    generate_assets_md5()
