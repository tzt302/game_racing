# Racing Line Pro — Telemetry Edition

使用 Python 与 Pygame 制作的轻量级方程式赛车游戏。

## 核心功能

- **真实遥测赛道**：斯帕、银石、蒙扎、摩纳哥和上海均基于 2025 排位赛最快圈 X/Y/Z 遥测，每约 5 米一个采样点。
- **真实驾驶参考**：赛车线、刹车、收油、目标速度、挡位和 RPM 均取自对应排位赛圈。
- **F1 三计时段**：真实 Sector 1/2 分界、毫秒计时，以及紫色全场最快、绿色个人提升、黄色未提升状态。
- **完整成绩比较**：分段时间、个人最快圈和全场最快圈/车手实时显示。
- **线性模拟输入**：LT/RT 从 0% 到 100% 完整映射物理行程。
- **速度相关物理**：渐进转向、轮胎抓地极限、侧滑、自动 8 挡变速箱和换挡动力中断。
- **多车 AI**：五名具有不同速度、侵略性和稳定性的 AI，会尝试超车、发生小失误并进行车体接触。
- **动态声音**：六层 CC0 发动机循环随 RPM 交叉混合，并包含换挡、轮胎和路面反馈。
- **三种视角**：高位 Halo T-Cam、低位 2.5D 驾驶舱与旋转俯视追踪视角可随时切换。
- **完整赛道表面**：沥青、红白路肩、缓冲区、草地和护栏具有不同交互。

## 操作

| 按键 | 功能 |
| --- | --- |
| `W` / `↑` | 油门 |
| `S` / `↓` | 刹车 |
| `A D` / `← →` | 转向 |
| `C` / `V` | 循环切换 T-Cam、驾驶舱和俯视视角 |
| `R` | 回到赛道 / 重新开始 |
| `Esc` | 暂停 |
| `F1` | 打开车手指南 |
| `L` | 显示或隐藏赛车线 |
| `B` | 显示或隐藏刹车标记 |

手柄默认使用左摇杆转向、RT 线性油门、LT 线性刹车、A 确认/回到赛道、Start 暂停。

## 运行与测试

```powershell
python -m pip install -r requirements.txt
python main.py
python -m unittest discover -s tests -v
```

构建 Windows EXE：

```powershell
pyinstaller --noconfirm --clean RacingLinePro.spec
```

重新导入 FastF1 遥测（仅开发者需要）：

```powershell
python -m pip install -r requirements-dev.txt
python tools/import_fastf1_tracks.py
```

数据、音频来源和许可信息见 [TRACK_SOURCES.md](TRACK_SOURCES.md)。

本项目是非官方作品，与 Formula 1、车队、车手或任何赛道运营方无关联。
