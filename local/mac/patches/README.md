# 建议补丁（需与团队协商后再合并到主代码）

这些改动**尚未应用**到主仓库，仅供团队评审。  
目标是让 Mac/Windows 共用同一套代码，通过环境变量区分端口，而不是各改各的配置文件。

## app-port-env.patch

将 `app.py` 末尾的硬编码端口改为读取环境变量，默认值仍为 `5000`（Windows 标准）：

```python
# 改前
app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

# 改后
port = int(os.environ.get("BACKEND_PORT", "5000"))
app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
```

Mac 开发者只需在 `local/mac/.env` 中设置 `BACKEND_PORT=5001`，无需再维护两份 `vite.config.js`。

## 如何提交给团队

1. 在组内说明：默认行为不变，Windows 无需任何改动
2. 全组同意后，由一人提交 PR 合并此改动
3. 合并后 Mac 端可逐步弃用 `local/mac/vite.config.js`，统一用主配置 + `.env`
