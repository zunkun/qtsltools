# qtsltools 项目长期备忘

## GitHub Release「数据仓库」同步
- 仓库 github.com/zunkun/qtsltools，Release tag=`database`（标题「数据仓库」）只作数据仓库：update.json / 最新APK / data zip；不更新代码。
- 同步脚本：根目录 `syncrelease.py`（依赖 gh CLI）。规则：update.json 每次强制覆盖；apk/zip 按 update.json 清单，线上已有同版本跳过；旧版本默认保留；about.json/privacy/favicon.ico 等其他资源不动。
- 发布流程：出新包 → `hashfile.py` 刷新 update.json/md5.txt → `syncrelease.py`（可先 --dry-run）。
- gh CLI 用 winget 安装在 `C:\Program Files\GitHub CLI\gh.exe`，旧终端 PATH 不刷新，脚本已做自动定位。

## 相关脚本职责
- `hashfile.py`：扫描 assets/ 生成 update.json + md5.txt（apk 取最高版本；zip v106/v108 固定配置，>108 沿用 108 的 minApkCode）。
- `syncdbfile.py`：把 webapi 的 sqlite 打包成 data-vX.zip 复制进 assets/，并同步 D:\share。
