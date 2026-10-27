# DeepArk

基于 AstrBot + NapCat 的 QQ 机器人 deepark。此仓库管理自研 companion 插件、人设、测试和维护记录；生产登录态、密钥、聊天与记忆数据不入库。

当前源码基线：companion **v0.6.0**，与 2026-10-27 核对的线上插件一致。详见 [基线记录](docs/BASELINE.md)。

## 开始开发

本地和服务器上的工作目录均由开发者自行选择。以下命令从仓库根目录执行：

```sh
git clone git@github.com:GrainRainAndy/DeepArk.git
cd DeepArk
git switch -c feat/your-task
python3 -m unittest discover -s tests -v
```

本地单元测试只依赖 Python 标准库，不需要 `.env`、QQ 登录或生产配置。完整 AstrBot SDK 测试需对应环境，见 [测试说明](docs/TESTING.md)。生产 Python 为 3.12.15；本地 59 项测试也已在 Python 3.9.6 通过，不代表整个插件支持旧版 AstrBot/Python。

## 导航

- [开发流程](CONTRIBUTING.md)：任务、分支、PR、远端协作与发布约定。
- [AI 协作约定](AGENTS.md)：作用范围和操作边界。
- [当前运行状态与运维](OPERATIONS.md)：生产核对、发布与回滚。
- [基线与待办](docs/BASELINE.md)：已核实事实及尚未建设的设施。
- [群聊参与](GROUP_PARTICIPATION.md)、[分层记忆](LAYERED_MEMORY.md)、[短消息聚合](SHORT_MESSAGES.md)、[社交判断](SOCIAL_DECISION.md)。

## 目录

| 路径 | 内容 |
|---|---|
| `plugin/` | 自研 companion 代码及配置 schema |
| `tests/` | 离线单元测试 |
| `container_*.py` | SDK 测试或在线探针，须按测试说明区分 |
| `persona.txt` | 人设文本；不是完整生产配置 |
| `ecosystem/` | 第三方插件整合脚本与历史记录 |
| `benchmarks/` | 合成模型探针与历史报告，执行会调用外部服务 |
| `deploy_*.py` 等根目录脚本 | 历史部署/激活/检查工具，不能批量运行或当成通用安装器 |

`GOAL.md`、`PROGRESS.md`、`ACCEPTANCE.md` 及 `ecosystem/README.md` 保留阶段历史；其中旧授权、状态和测试数字不是当前状态，也不构成新任务的操作授权。当前状态以 `OPERATIONS.md` 和带日期的基线核对为入口。

本轮仅建立仓库与文档。尚未配置自动 CI、分支保护、隔离测试容器或统一部署器；流程约定不等于这些设施已经启用。
