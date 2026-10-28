> 历史资料：保留当时路径、命令和状态；当前操作请见 [运维说明](../OPERATIONS.md)，旧脚本去向见 [清理清单](../SCRIPT_INVENTORY.md)。

# 仓库基线：2026-10-27

## 本轮范围

建立 `GrainRainAndy/DeepArk` 初始源码和多人协作文档。保持业务代码、生产服务与生产配置不变；不限制开发者路径，不配置单独测试 QQ。

## 来源与核对

源码来自原本地 `AliyunECS/deepark` 工作目录。2026-10-27 通过 SSH 对生产 `/home/grainrain/astrbot/data/plugins/astrbot_plugin_deepark_companion` 读取 SHA-256；全部 10 个 Python 文件、`_conf_schema.json`、`metadata.yaml` 与本地逐一一致。清单见 [baseline-plugin.sha256](baseline-plugin.sha256)。

校验清单保留原始 `plugin/` 路径及校验值；当前目录已迁移，从仓库根目录提取历史版本到临时目录核对：

```sh
baseline_dir=$(mktemp -d)
git archive 07f5133 | tar -x -C "$baseline_dir"
(cd "$baseline_dir" && shasum -a 256 -c docs/baseline-plugin.sha256)
```

这是初始基线校验，未来修改代码后出现不匹配是正常的；不要把它当作每个 PR 都应通过的测试，也不要静默重写历史清单。

- companion：v0.6.0。
- 生产 Python：3.12.15；已有功能记录中的 AstrBot：4.29.3（本轮未独立查询应用版本）。
- 运行容器的 image ID：`sha256:c93a6d19507ba45474c3dfb82aad9d36eb432a478112f13c7e6325b5ebffc5f2`。
- 配置镜像标签仍为 `latest`，image ID 不等于可拉取的 registry digest；本轮未固定 Compose 镜像。
- 本地执行 `python3 -m unittest discover -s tests -v`：59 项通过。
- 本轮不重新执行 SDK/在线模型/QQ 验收，不把历史结果称为本轮验证。

这份基线只确认自研插件源码一致，不声称仓库能完整重建生产。生产人设数据库、第三方插件、密钥及全部运行配置未导出。`persona.txt` 是本地维护文本，本轮未与生产数据库逐字比对。

## 收录与排除

收录自研源码、人设、离线/SDK 测试、历史部署与探针脚本、经人工撰写的功能/评估记录。历史脚本保留原路径和当时参数，不包装成通用工具。已有操作记录含特定会话标识，属于运维元数据；发布到更广范围前需评估是否脱敏。

不收录 `.env`、数据库、QQ 登录态、备份、缓存、原始模型 JSONL、AstrBot 参考源码快照及大肥鱼参考配置包。本地原文件保留，不因忽略而删除。参考资料不是运行依赖；第三方代码许可证未作统一重授权，不为整个仓库擅自增加许可证。

`.gitignore` 的分组标题参照本机 `GitHub/c_cpp`，简短说明和根目录路径写法参照 `GitHub/ReT-Markdown`，按 AstrBot/NapCat 实际状态文件调整。共享 `AGENTS.md` 纳入版本管理；个人 SSH 配置不入库。

## 后续工作（本轮不实施）

- 自动 CI、分支保护和 reviewer 设置。
- 独立远端 SDK 测试环境及依赖锁定。
- 通用部署入口、发布锁、发布记录与回滚演练。
- 配置模板、第三方插件版本清单和可复现镜像固定。
- 历史脚本路径参数化，按用途整理工具。

开发流程中的这些目标尚未成为已运行设施。
