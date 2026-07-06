后端说明（重要配置与跨平台约束）

1) AI 信息来源策略

- 配置项：`AI_INFO_SOURCE_STRATEGY`
- 位置：`movie-system/backend/config.py`（支持通过环境变量覆盖，例如 `AI_INFO_SOURCE_STRATEGY=internal_only`）
- 可选值：
  - `internal_only`：仅使用系统内部数据，禁止任何联网搜索（用于严格离线/安全场景）。
  - `internal_first`：优先使用系统内部数据，必要时允许联网补充（默认，适用于 Windows 生产环境）。
  - `web_allowed`：允许优先或同时使用联网数据（仅用于特殊调试，不推荐生产使用）。
- 目的：确保系统以仓库内数据为主、联网为辅，符合团队对 AI 回答来源的策略要求。

2) 系统级配置约定（必须遵守）

- 所有系统级地址/端口/开关（例如 Spark VM 地址 `SPARK_VM_URL`、`SPARK_VM_ENABLED` 等）必须放在 `movie-system/backend/config.py` 中，并以 `os.environ.get()` 提供覆盖。默认值请使用 Windows 生产环境的设置。
- 不要把系统级默认值硬编码到 Mac 专属文件或开发脚本中。

3) Mac 专属文件与 Mock

- 所有 Mac 本地辅助脚本、Mock 服务器或仅在 Mac 上使用的配置必须放在 `local/mac/` 目录下（例如 `local/mac/start-mac.sh`、`local/mac/stop-mac.sh`、mock 脚本、`local/mac/CROSS_PLATFORM_COMPATIBILITY.md` 等）。
- 禁止直接修改仓库根的 `start-system.bat`、主路径常量或 `movie-system/backend/config.py` 的生产默认值以适配 Mac。

4) 路径与平台兼容性

- 代码中所有路径必须使用 `pathlib.Path` 处理，禁止硬编码 Windows 盘符（例如 `C:\`）或 Unix 用户主目录短写（例如 `~`）。
- 当需要不同的启动脚本时，请分别提供 `local/mac/*.sh` 与仓库根对应的 `*.bat`（功能应保持对齐）。

5) 依赖与运行时注意项

- 若使用 MySQL 8 且采用 `caching_sha2_password` 或 `sha256_password` 认证，运行时需要 `cryptography` 包支持。已将 `cryptography>=40.0.0` 添加到 `movie-system/backend/requirements.txt`。
- Python 版本：3.11+（仓库以 Python 3.11+ 为目标）。尽量使用标准库实现，新增第三方依赖需在 `requirements.txt` 列出并说明必要性。

如需变更或新增系统级配置，请先在 `movie-system/backend/config.py` 中添加配置项并以 `os.environ.get()` 暴露，然后通过代码审查与团队成员同步合并。