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

# 写死固定配置：data‑v106 / data‑v108
FIXED_ZIP_CONFIG = {
    "data-v106.zip": {
        "minApkCode": 100,
        "changelog": "题材统计资源"
    },
    "data-v108.zip": {
        "minApkCode": 124,
        "changelog": "题材统计资源"
    }
}
# 大于108的新版本，复制 data‑v108 的配置
ABOVE_108_TPL = FIXED_ZIP_CONFIG["data-v108.zip"]
# =================================================


def calc_md5(file_path: Path, chunk_size=65536) -> str:
    """计算文件md5"""
    md5_obj = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5_obj.update(chunk)
    return md5_obj.hexdigest()


def extract_version_code(filename: str) -> Optional[int]:
    """
    从文件名提取版本号
    qtsl-v124.apk → 124
    data-v108.zip →108
    匹配模式: *-v<num>.ext
    """
    m = re.search(r"-v(\d+)\.", filename)
    if m:
        return int(m.group(1))
    return None


def load_update_json() -> Dict[str, Any]:
    """加载已有update.json，不存在返回基础模板"""
    if UPDATE_JSON.exists():
        with open(UPDATE_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    # 基础模板
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

    # 处理APK
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

        if fname in FIXED_ZIP_CONFIG:
            # data‑v106 / data‑v108 使用写死配置
            conf = FIXED_ZIP_CONFIG[fname]
            entry = {
                "versionCode": ver,
                "minApkCode": conf["minApkCode"],
                "name": fname,
                "md5": md5_val,
                "changelog": conf["changelog"]
            }
            print(f"📄 {fname} 使用固定写死配置")
        else:
            # >108 的新版本，复制108模板
            entry = {
                "versionCode": ver,
                "minApkCode": ABOVE_108_TPL["minApkCode"],
                "name": fname,
                "md5": md5_val,
                "changelog": ABOVE_108_TPL["changelog"]
            }
            print(f"📄 {fname} 版本>108，复制data‑v108配置模板")
        zip_items.append(entry)

    # zip按versionCode降序
    zip_items.sort(key=lambda x: x["versionCode"], reverse=True)

    # 更新apk块
    if latest_apk_path is not None:
        apk_md5 = calc_md5(latest_apk_path)
        cfg["apk"]["name"] = latest_apk_path.name
        cfg["apk"]["md5"] = apk_md5
        cfg["apk"]["versionCode"] = latest_apk_ver
        cfg["apk"]["versionName"] = f"{latest_apk_ver//100}.{(latest_apk_ver%100)//10}.{latest_apk_ver%10}"

    cfg["dataPackList"] = zip_items

    # 写回json
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
