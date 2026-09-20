#!/usr/bin/env python3
import hashlib
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any

# ===================== 配置 =====================
SCRIPT_PATH = Path(__file__).resolve()
ASSET_DIR = SCRIPT_PATH.parent / "assets"
OUTPUT_MD5_TXT = ASSET_DIR / "md5.txt"
UPDATE_JSON = ASSET_DIR / "update.json"

# 固定版本配置，仅磁盘存在该文件时才输出该条目
FIXED_ZIP = {
    106: {"minApkCode": 100, "changelog": "题材统计资源"},
    108: {"minApkCode": 124, "changelog": "题材统计资源"},
}
# versionCode >108 的数据包，统一参照108的minApkCode
BASE_108 = FIXED_ZIP[108]
# =================================================


def calc_md5(file_path: Path, chunk_size=65536) -> str:
    md5_obj = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5_obj.update(chunk)
    return md5_obj.hexdigest()


def extract_version_code(filename: str) -> Optional[int]:
    m = re.search(r"-v(\d+)\.", filename)
    if m:
        return int(m.group(1))
    return None


def load_update_json() -> Dict[str, Any]:
    if UPDATE_JSON.exists():
        with open(UPDATE_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "apk": {
            "enable": True,
            "versionName": "0.0.0",
            "versionCode": 0,
            "name": "",
            "md5": "",
            "forceUpdate": True,
            "changelog": "软件更新,修复Bug"
        },
        "dataPackList": []
    }


def generate_assets_info():
    ASSET_DIR.mkdir(exist_ok=True)

    apk_files = list(ASSET_DIR.glob("qtsl*.apk"))
    zip_files = list(ASSET_DIR.glob("data*.zip"))

    print(f"🔍 找到APK: {len(apk_files)} 个 | ZIP数据包: {len(zip_files)} 个")

    # 处理APK，取版本最大
    valid_apks = []
    for p in apk_files:
        ver = extract_version_code(p.name)
        if ver is not None:
            valid_apks.append((ver, p))
        else:
            print(f"⚠️ 无法解析版本号，跳过: {p.name}")

    latest_apk_path: Optional[Path] = None
    latest_apk_ver: int = 0
    if valid_apks:
        valid_apks.sort(key=lambda x: x[0], reverse=True)
        latest_apk_ver, latest_apk_path = valid_apks[0]
        print(f"📦 选中最新APK: {latest_apk_path.name} , versionCode={latest_apk_ver}")

    cfg = load_update_json()
    zip_items = []

    for p in zip_files:
        fname = p.name
        ver = extract_version_code(fname)
        if ver is None:
            print(f"⚠️ 无法解析版本号，跳过zip: {fname}")
            continue
        md5_val = calc_md5(p)

        if ver in FIXED_ZIP:
            # 106 /108，使用固定配置；没有实体文件直接不会进入这里
            conf = FIXED_ZIP[ver]
            entry = {
                "versionCode": ver,
                "minApkCode": conf["minApkCode"],
                "name": fname,
                "md5": md5_val,
                "changelog": conf["changelog"]
            }
            print(f"📄 {fname} 使用固定配置 ver={ver}")
        else:
            # >108 全部沿用108的minApkCode，changelog沿用108模板
            entry = {
                "versionCode": ver,
                "minApkCode": BASE_108["minApkCode"],
                "name": fname,
                "md5": md5_val,
                "changelog": BASE_108["changelog"]
            }
            print(f"📄 {fname} ver>{108}，参照108配置")
        zip_items.append(entry)

    # 按versionCode降序输出
    zip_items.sort(key=lambda x: x["versionCode"], reverse=True)

    # 更新apk块，保留原有其他字段
    if latest_apk_path is not None:
        apk_md5 = calc_md5(latest_apk_path)
        cfg["apk"]["name"] = latest_apk_path.name
        cfg["apk"]["md5"] = apk_md5
        cfg["apk"]["versionCode"] = latest_apk_ver
        cfg["apk"]["versionName"] = f"{latest_apk_ver//100}.{(latest_apk_ver%100)//10}.{latest_apk_ver%10}"

    cfg["dataPackList"] = zip_items

    with open(UPDATE_JSON, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f"✅ update.json 已写入: {UPDATE_JSON.resolve()}")

    # md5.txt
    all_target = []
    if latest_apk_path:
        all_target.append(latest_apk_path)
    all_target.extend(zip_files)
    lines = []
    for f in all_target:
        h = calc_md5(f)
        lines.append(f"{f.name} {h}")
        print(f"{f.name} {h}")
    OUTPUT_MD5_TXT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n✅ MD5清单已保存至：{OUTPUT_MD5_TXT.resolve()}")


if __name__ == "__main__":
    try:
        generate_assets_info()
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        raise
