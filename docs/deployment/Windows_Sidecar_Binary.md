# Windows 侧车可执行文件（PyInstaller）

## 产物

- **GitHub Release（推荐）：** 推送形如 **`v0.2.1`** 的标签后，由 **`.github/workflows/release.yml`** 在 **`windows-latest`** 上构建 **`pyc-hermes-sidecar.exe`**（onefile、控制台），并作为 Release 资产上传。
- **本地 Windows 构建：**

```powershell
# 仓库根目录
uv sync --frozen --extra ga
uv run pyinstaller --noconfirm packaging\pyinstaller\pyc_hermes_sidecar_onefile.spec
# 输出: dist\pyc-hermes-sidecar.exe
```

或使用 **`scripts/build_sidecar_windows.ps1`**（封装上述命令）。

## 运行时约定

与源码侧车相同：通过 **`--root`** 指向工作区（或使用默认解析路径）。日志与数据目录仍遵循 **`docs/constraints/windows-packaging.md`**（`%APPDATA%` / `%LOCALAPPDATA%`），**不要** 在安装目录写入可变数据。

## 限制（诚实范围）

- **非** 代码签名安装器；商业上架需另行列项签名与更新通道。
- onefile 首次启动有解包延迟；进程防病毒误报风险由发布方评估。
- Electron 桌面壳仍为独立产物；本 exe **仅** 打包 **Python 侧车 HTTP**。
