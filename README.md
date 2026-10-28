# DeepArk

基于 AstrBot + NapCat 的 QQ 机器人 deepark。本仓库管理自研插件、人设、测试及维护工具；生产密钥、QQ 登录态、聊天与记忆数据不入库。

## 目录

```text
plugins/
  deepark_companion/       # companion 插件完整源码、schema、metadata
resources/
  persona.txt             # 维护中的人设文本
scripts/
  diagnostics/            # 线上只读检查（需 AstrBot SDK/生产环境）
  evaluation/             # 真实模型与 embedding 评估，会调用外部服务
  maintenance/            # 人设回滚等维护操作，会修改生产
tests/                    # 详见下方测试命令
  unit/                   # 标准库离线测试
  integration/            # AstrBot SDK 测试；临时数据、模拟发送/模型
docs/
  features/               # 记忆、群参与、短消息聚合等说明
  history/                # 旧部署记录、基线与性能报告
  plans/                  # 后续重构计划
```

新增插件放在 `plugins/<plugin_name>/`，保持插件内部相对导入。`plugins/deepark_companion/` 的内容对应服务器的 `astrbot_plugin_deepark_companion` 目录；仓库目录调整不改变线上目录和插件 ID。

## 开发与测试

从仓库根目录运行：

```sh
python3 -m unittest discover -s tests/unit -v
```

单元测试只依赖 Python 标准库。SDK 测试需要匹配的 AstrBot 环境，运行方式见 [测试说明](docs/TESTING.md)。不要批量执行 `scripts/`，其中部分会调用付费模型或修改生产。

## 导航

- [开发流程](CONTRIBUTING.md)、[协作约定](AGENTS.md)
- [当前运维](docs/OPERATIONS.md)、[脚本分类和清理清单](docs/SCRIPT_INVENTORY.md)
- [群聊参与](docs/features/GROUP_PARTICIPATION.md)、[分层记忆](docs/features/LAYERED_MEMORY.md)
- [短消息聚合](docs/features/SHORT_MESSAGES.md)、[社交判断](docs/features/SOCIAL_DECISION.md)
- [目录整理与后续重构计划](docs/plans/2026-10-28-repository-layout.md)
- [初始基线](docs/history/BASELINE.md)

旧部署、授权和初始化脚本已清理，仍可从 Git 历史查看。通用部署器、发布锁、CI 和独立 SDK 测试镜像尚未建立，详见重构计划。
