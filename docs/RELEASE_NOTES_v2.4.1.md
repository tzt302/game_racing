# Racing Line Pro v2.4.1

这是 2.4.0 的 Windows 启动热修复。

## 修复内容

- 修复启动时出现 `ModuleNotFoundError: No module named 'game'` 的问题。
- PyInstaller 现在会在分析阶段正确搜索 `src`，并把游戏运行包收集进单文件 EXE。
- 操控、计时、AI 和赛道内容与 2.4.0 保持一致。
- 继续保持无声音效果，发行包不包含游戏音频素材。

## 验证

- 自动化测试全部通过。
- 包内确认存在 `game.loop`、`physics.vehicle`、`track.track` 和 `ui.hud`。
- Windows 启动测试确认出现 `Racing Line Pro v2.4.1` 游戏窗口，而不是错误对话框。

请下载 `RacingLinePro-v2.4.1.exe`，不要继续使用无法启动的 2.4.0 EXE。
