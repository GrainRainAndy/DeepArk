# 仓库目录整理与后续重构计划

> 执行方式：逐项实施、验证并更新勾选状态；后续任务使用 superpowers:executing-plans。

**Goal:** 为多个插件预留独立目录，清理根目录及已失效的一次性脚本。

**Architecture:** 插件按名称放在 plugins/ 下；离线单元测试与 SDK 集成测试隔离；运行工具按诊断、评估、维护分类。历史脚本从工作树删除，通过 Git 保留可追溯版本。

**Tech Stack:** Python 标准库 unittest；集成测试额外依赖 AstrBot 4.29.3。

**Spec:** 用户要求 plugin 增加二级目录、整理 scripts、计划重构并清理过期脚本。

## 约束与检查重点

- 本轮不改变插件运行逻辑、服务器目录、生产配置或服务。
- 自研插件目录为 plugins/deepark_companion/；部署时该目录内容对应服务器 astrbot_plugin_deepark_companion。
- 不运行在线模型探针、部署或维护脚本。文件迁移与语法检查不等于在线工具验证。
- 保留测试覆盖；更新所有导入路径及 mock patch 目标。
- 历史文档标明历史上下文；删除脚本的原路径和依据单独登记。
- 检查跨文件导入、文档相对链接、资源文件路径、测试发现边界、旧基线校验路径。

## 本轮实施

- [x] 将 plugin/ 迁至 plugins/deepark_companion/，插件内部保持相对导入。
- [x] 将单元测试迁至 tests/unit/；四个无真实发送的 SDK 测试迁至 tests/integration/，修正旧 allow_groups 用例为白名单移除场景。
- [x] 诊断移至 scripts/diagnostics/，在线模型评估移至 scripts/evaluation/，人格回滚移至 scripts/maintenance/。
- [x] 删除旧部署/授权/生态初始化/会话修复脚本及被 backend_compare.py 覆盖的 backend.py；登记恢复方法与依据。
- [x] 人设归入 resources/；功能文档归入 docs/features/，历史记录归入 docs/history/，更新导航与命令。
- [x] 执行全部离线单元测试、Python AST 解析、文档链接检查与 git diff --check；SDK 缺少依赖则明确记录未运行。

## 后续重构（本轮不实施）

### 1. 统一工具参数与副作用边界

涉及 scripts/evaluation/*.py、scripts/diagnostics/*.py、scripts/maintenance/rollback_persona.py。
为每个工具增加 main() 与 argparse；提供 --data-dir、--provider、--persona、--audio 参数，替代固定服务器路径和 /tmp 输入。提取 scripts/common/config.py，密钥只在执行时读取。维护命令增加明确目标与预览。测试 import 不发请求、不读取生产文件，缺失输入先报错；以模拟 HTTP 验证请求与错误脱敏。

### 2. 可复现的 SDK 测试环境

为 tests/integration/ 配置与生产匹配的依赖或固定镜像，使用独立容器和临时存储，不挂载生产 data。运行全部 SDK 测试并更新适配器兼容性记录；加入离线 CI 和独立 SDK job。验收：任意干净 checkout 可按文档运行，测试不连接 QQ 和真实模型。

### 3. 按插件统一打包与发布

新增 scripts/deploy/ 入口，接受插件名称和明确的源目录，只打包对应 plugins/<name>/。先建立文件清单、校验值、备份与代码回滚测试，再设计原子替换、发布锁和健康检查。不要复活旧部署脚本中写死的配置迁移。模拟失败验证回滚不覆盖配置和数据库；生产部署另行安排。

### 4. 拆分 companion 内部职责

在 SDK 回归可运行之后，将 main.py 的授权判断、群参与和公开资料接入逐步提取到同插件子模块；Store 的记忆与调度存储分别评估拆分。每一步保持事件钩子顺序、限额和撤回语义，有现有行为测试再迁移，不同时改变功能。

## 本轮验证记录

- 基于提交 `676d81d`，分支 `refactor/repository-layout` 的未提交修改。
- 63 项离线单元测试通过；全部 40 个 Python 文件 AST 解析通过。
- 插件的 12 个源码/schema/metadata 文件与整理前 HEAD 字节一致，未改变运行逻辑。
- SDK 测试启动受本地环境阻碍：test_adapter、test_participation、test_public_profile 缺少 astrbot 包；test_batching 在本地 Python 3.9 缺少 contextlib.aclosing（SDK 验证目标为 Python 3.12）。未声称集成测试通过。
- 所有 Markdown 相对链接可解析，git diff --check 通过，根目录 Python 脚本为 0。
- 未执行线上工具，未修改或重启生产；本轮在线工具只做路径检查与语法验证。
- 本地被忽略的 reference/、dafeiyu-config-pack/ 和 benchmarks/ 原始采样数据保留，不属于 Git 仓库结构或本轮删除范围。
- 独立只读审查完成：未发现重要问题；SDK 集成行为仍需匹配环境验证。
