跨平台兼容性约束（重要）

- 系统级配置（如 Spark VM 地址、端口、开关等）统一放在仓库后端配置文件：movie-system/backend/config.py，并支持通过 `os.environ.get()` 覆盖；默认值按 Windows 生产环境设置。请勿在本文件中写入仅用于 Mac 的专属默认值。
- Mac 专属辅助脚本与 Mock 必须放在 `local/mac/` 目录下（例如 `start-mac.sh`、`stop-mac.sh`、mock 服务器脚本等），避免修改仓库根目录下的 Windows 启动脚本 `start-system.bat` 或主路径常量。
- 所有路径相关代码请使用 Python 的 `pathlib.Path` 处理，禁止硬编码 Windows 盘符（如 `C:\`) 或 macOS 绝对主目录符号（如 `~`)。
- 若需不同的启动命令或脚本（shell vs batch），请分别提供 `local/mac/*.sh` 与仓库根目录对应的 `*.bat`，两者功能需对齐。

如有疑问或需新增系统级配置，请先在 `movie-system/backend/config.py` 中添加并以 `os.environ.get()` 暴露为可覆盖项，然后通知团队成员同步变更。谢谢配合。
