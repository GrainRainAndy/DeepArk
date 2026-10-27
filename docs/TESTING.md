# 测试说明

所有命令在仓库根目录执行，开发目录不作限制。

## 离线单元测试

```sh
python3 -m unittest discover -s tests -v
```

仅依赖标准库；使用临时数据库和合成输入，不需要生产密钥。2026-10-27 基线验证：59 项通过。

## AstrBot SDK 回归

以下四个文件使用真实 SDK 类型、模拟发送/模型接口和临时数据：

```sh
python -m unittest container_integration container_batching container_public_profile container_participation -v
```

需要与生产匹配的 AstrBot SDK 和依赖（已有记录为 AstrBot 4.29.3，生产 Python 3.12.15）。这不是纯标准库测试，不能把 `reference/astrbot` 源码快照当成完整安装环境。

应在独立进程/隔离环境中运行，使用可写临时目录，不挂载生产数据，不启动平台连接。独立容器及一键环境配置尚未建立，本轮没有重新执行 SDK 回归；已有历史结果见功能文档。当前不要把生产容器当作大家共享的随意执行环境，需要使用时由维护者协调具体命令和影响。

## 其他脚本不是默认测试

| 文件 | 行为与边界 |
|---|---|
| `container_media.py`、`container_social.py` | 读取生产 provider 配置并调用真实模型，可能计费 |
| `probe_*.py`、`evaluate_*.py`、`benchmarks/*.py` | 外部接口探针/评估；逐个审阅输入、费用和依赖 |
| `ecosystem/verify_memory.py` | 云 embedding 与临时索引验证，依赖现有配置 |
| `verify_batching_live.py`、`verify_public_profile_live.py` | 线上配置/SDK 检查，需生产访问；不属于离线单元测试 |
| `deploy_*.py`、`activate_group.py`、`authorize_current_group.py`、`upgrade_plugin.py`、`rollback_persona.py`、`ecosystem/` 管理脚本 | 可能修改生产配置、数据库或服务，不是测试入口 |

不要使用 `python container_*.py` 式的批量循环来执行所有脚本。

## 无测试 QQ 的验收边界

自动回归只模拟发送，不向真实 QQ、群或空间发消息。代码测试通过不证明 QQ 媒体下载、网络发送和真实用户体验全部正常。

真实链路验证单独安排生产窗口，写清目标会话、操作、预期、失败停止条件与恢复办法。主动测试消息需要具体授权；日常观察用户自发交互时，只记录脱敏现象，不能把私聊和群记录提交到仓库。
