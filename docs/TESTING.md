# 测试说明

所有命令从仓库根目录运行。生产插件路径不因仓库目录整理而变化。

## 离线单元测试

```sh
python3 -m unittest discover -s tests/unit -v
```

只依赖 Python 标准库，使用临时数据库和合成输入，不需要生产配置或 QQ 登录。本次目录迁移的验证结果见重构计划。

## AstrBot SDK 集成测试

```sh
python -m unittest discover -s tests/integration -t . -v
```

四个测试模块：`test_adapter.py`、`test_batching.py`、`test_public_profile.py`、`test_participation.py`。它们引用 `plugins.deepark_companion`，使用 SDK 事件、临时存储和模拟发送/模型，不调用真实 QQ 或模型。

需要与生产匹配的 AstrBot SDK 和依赖（现有记录为 AstrBot 4.29.3 / Python 3.12.15）。应在独立进程或隔离环境运行，不挂载生产 data、不启动平台连接。独立环境和依赖锁定尚未建立；本地缺少 SDK 时不能用语法检查代替测试通过。

不要使用 `discover -s tests` 混跑两个层级。跨模块测试辅助类由 `tests.integration` 导入；集成测试不应被默认离线命令发现。

## 在线工具与维护操作

- `scripts/evaluation/`：读取服务器配置并调用真实模型/embedding，可能计费，不是自动测试。
- `scripts/diagnostics/`：检查已安装代码、配置和会话状态，需对应生产 SDK；不能冒充无环境依赖的单元测试。
- `scripts/maintenance/rollback_persona.py`：读取历史备份、更新人设并重启服务，不是测试。

各脚本的环境与输入见 [脚本清单](SCRIPT_INVENTORY.md)。不得 glob 执行脚本或导入在线探针来做测试发现。

## QQ 验收

自动回归只模拟发送，不向真实 QQ/群发送消息。真实收发另行指定目标、动作和验证窗口；不克隆 QQ 登录态，不将生产凭据或聊天数据库复制到开发机器。
