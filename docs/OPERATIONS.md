# 当前运行与运维

最后核对：2026-10-28。本文记录核对时事实，不保证后续线上状态不变。开发流程见 [CONTRIBUTING.md](../CONTRIBUTING.md)，历史操作见 [历史运维](history/HISTORICAL_OPERATIONS.md)。

## 当前生产

- 连接：`ssh aliyun-ecs`。主目录 `/home/grainrain/astrbot`，Compose 文件 `astrbot.yml`。
- 容器 `astrbot` 与 `napcat` 在核对时均运行；`/home/grainrain/astrbot/data` 绑定到 `/AstrBot/data`。
- 自研插件：`data/plugins/astrbot_plugin_deepark_companion`，v0.6.0；12 个源码/schema/元数据文件与本地完全一致。
- 配置：`data/config/astrbot_plugin_deepark_companion_config.json`；核对到 `enabled=true`、`proactive_enabled=true`、`dry_run=false`、`auto_memory=false`。2026-10-28 起群授权直接读取各会话有效 AstrBot 配置的 `platform_settings.id_whitelist`，取消独立 `allow_groups`；当前两个群（含测试群）获得授权。每次检查重新读取，增删白名单随有效配置立即生效。关闭白名单总开关不会使 companion 向所有群开放；仍要求显式群条目，空列表拒绝全部群。私聊及其他平台 UMO 不授权当前群。
- 群参与的规则见 [GROUP_PARTICIPATION.md](features/GROUP_PARTICIPATION.md)。不要继续使用旧记录的“群未授权、主动关闭”描述。
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

统一部署器、发布锁和 CI 尚未建立。旧的一次性部署脚本已从工作树移除，清理依据见 [脚本清单](SCRIPT_INVENTORY.md)。生产插件目录不变；仓库源目录为 `plugins/deepark_companion/`，部署时取其内容。后续工具计划见 [重构计划](plans/2026-10-28-repository-layout.md)。

1. 指定一位发布人，确认无人正在变更生产；约定维护窗口。
2. 确认待发 commit 已合并至 `main`，记录测试证据及与线上版本的差异。
3. 写清受影响文件/配置、是否迁移数据库及恢复办法。备份到服务器受限目录；需要一致性快照时安排停写或使用 SQLite backup，不在写入中随意复制数据库。
4. 仅执行审核过的变更；通常只需重启 AstrBot，不因插件更新重启 NapCat。
5. 检查容器状态、插件加载、OneBot 连接和必要配置。不默认向真实群发送验收消息。
6. 记录发布结果及实际部署文件校验值。失败按本次恢复计划回滚并记录。

发布记录至少包括：时间、操作人、commit、插件版本、镜像 ID/digest、测试结果、配置差异、备份路径、健康检查、回滚入口。

## 回滚

2026-10-28 白名单同步部署：基于 `07f51335f077cfc2415a6317f034e5168873915f` 的工作区修改，`python3 -m unittest discover -s tests -v` 共 63 项通过，`git diff --check` 通过。线上代码读取正式配置与只读会话状态验证：两个白名单群允许、未列出的群拒绝；未发送测试消息。备份：`/home/grainrain/astrbot-backups/companion-whitelist-20261028-034116/`，含 main.py、schema 和插件配置；回滚只恢复这些文件并重启，不恢复数据库。部署 main.py SHA256：`df46193883c5a3ed790a5d6ac0b1fe8dba937fe23b7aa985f5bbbce0e6f32ea5`。公开资料授权仍由 `public_profile_sessions` 单独控制。

先核对“当前版本”和“要恢复的版本”，不能只选择名字最新的历史脚本。旧脚本可能恢复不同阶段配置，也可能不能删除新版本新增文件。

优先回退代码及受影响配置，保留期间新增的聊天、记忆和额度状态；若数据库格式不向后兼容，必须先准备迁移或专门的数据恢复方案。整库恢复会丢失备份之后的数据，不能作为普通代码回滚的默认步骤。

当前 v0.6.0 部署历史记录指向 `/home/grainrain/astrbot-backups/participation-20261027T095238Z`。此为追溯信息，本轮未执行其 rollback.sh，也未演练恢复。
