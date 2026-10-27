# 当前运行与运维

最后核对：2026-10-27。本文记录基线时事实，不保证后续线上状态不变。开发流程见 [CONTRIBUTING.md](CONTRIBUTING.md)，历史操作见 [历史运维](docs/HISTORICAL_OPERATIONS.md)。

## 当前生产

- 连接：`ssh aliyun-ecs`。主目录 `/home/grainrain/astrbot`，Compose 文件 `astrbot.yml`。
- 容器 `astrbot` 与 `napcat` 在核对时均运行；`/home/grainrain/astrbot/data` 绑定到 `/AstrBot/data`。
- 自研插件：`data/plugins/astrbot_plugin_deepark_companion`，v0.6.0；12 个源码/schema/元数据文件与本地完全一致。
- 配置：`data/config/astrbot_plugin_deepark_companion_config.json`；核对到 `enabled=true`、`proactive_enabled=true`、`dry_run=false`、`auto_memory=false`，授权群数量为 1。
- 群参与的规则见 [GROUP_PARTICIPATION.md](GROUP_PARTICIPATION.md)。不要继续使用旧记录的“群未授权、主动关闭”描述。
- LivingMemory 是普通长期记忆入口；companion 保留公开资料层及节奏管理。资料撤回与 LivingMemory 软归档不等于删除所有原始历史/备份。
- 生产数据和备份保留在服务器；路径 `/home/grainrain/astrbot-backups`。不纳入 Git，不复制到开发电脑。
- 当前 SSH 用户管理 Docker 需要 sudo。不会在本轮变更账号、权限或服务。

## 只读核对

```sh
ssh aliyun-ecs 'sudo -n docker ps --format "{{.Names}}\t{{.Image}}\t{{.Status}}"'
ssh aliyun-ecs 'sudo -n docker inspect astrbot --format "{{.Image}}"'
```

不要把完整 Docker inspect、生产配置或未脱敏日志粘贴进 PR，它们可能含凭据或真实会话内容。

## 发布约定（当前人工执行）

统一部署器、发布锁和 CI 尚未建立。现有 `deploy_*.py` 是历史操作记录，不是可以重复执行的通用部署命令。部署前必须审阅脚本中的固定暂存路径、会话断言、文件清单、配置覆盖和恢复逻辑。

1. 指定一位发布人，确认无人正在变更生产；约定维护窗口。
2. 确认待发 commit 已合并至 `main`，记录测试证据及与线上版本的差异。
3. 写清受影响文件/配置、是否迁移数据库及恢复办法。备份到服务器受限目录；需要一致性快照时安排停写或使用 SQLite backup，不在写入中随意复制数据库。
4. 仅执行审核过的变更；通常只需重启 AstrBot，不因插件更新重启 NapCat。
5. 检查容器状态、插件加载、OneBot 连接和必要配置。不默认向真实群发送验收消息。
6. 记录发布结果及实际部署文件校验值。失败按本次恢复计划回滚并记录。

发布记录至少包括：时间、操作人、commit、插件版本、镜像 ID/digest、测试结果、配置差异、备份路径、健康检查、回滚入口。

## 回滚

先核对“当前版本”和“要恢复的版本”，不能只选择名字最新的历史脚本。旧脚本可能恢复不同阶段配置，也可能不能删除新版本新增文件。

优先回退代码及受影响配置，保留期间新增的聊天、记忆和额度状态；若数据库格式不向后兼容，必须先准备迁移或专门的数据恢复方案。整库恢复会丢失备份之后的数据，不能作为普通代码回滚的默认步骤。

当前 v0.6.0 部署历史记录指向 `/home/grainrain/astrbot-backups/participation-20261027T095238Z`。此为追溯信息，本轮未执行其 rollback.sh，也未演练恢复。
