# 脚本清单与清理依据

2026-10-28；整理前版本：`676d81d4530cd3221e0a2eff5379027b1b8ee6cd`。本次只做仓库整理，没有运行任何线上诊断、评估、维护或部署脚本。

## 保留的工具

| 目录/文件 | 环境与作用 | 限制 |
|---|---|---|
| `scripts/diagnostics/verify_batching_live.py` | AstrBot 容器；读取正式配置，检查短消息聚合资格 | 依赖已安装插件和特定模型配置 |
| `scripts/diagnostics/verify_public_profile_live.py` | AstrBot 容器；正式配置 + 临时公开资料库 | 合成事实、模拟发送，不写生产记忆 |
| `scripts/maintenance/rollback_persona.py` | 服务器；接受人格备份目录参数 | 修改数据库中的人设并重启，执行前审阅备份 |
| `scripts/evaluation/backend_compare.py` | 服务器；支持 provider ID 参数，默认读取主模型 | 真实 API，单轮有界性能采样 |
| `scripts/evaluation/vision_probe.py` | AstrBot 容器；合成图片、deepark-vision | 真实 API |
| `scripts/evaluation/sdk_media.py` | AstrBot 容器；通过真实 SDK 验证视觉/ASR | 真实 API，需 `/tmp/deepark-synthetic.wav` |
| `scripts/evaluation/sdk_social.py` | AstrBot 容器；已安装 companion 的社交判断 | 真实 API |
| `scripts/evaluation/probe_audio.py` | 服务器；合成 ASR 音频输入 | 需 `/tmp/deepark-synthetic.wav`；Paratera 专用 |
| `scripts/evaluation/probe_media.py` | 服务器；合成视觉输入 | Paratera 专用，读取主模型来源 |
| `scripts/evaluation/probe_tts_catalog.py` | 服务器；查询模型目录 | Paratera 专用 |
| `scripts/evaluation/evaluate_persona.py` | 服务器；评估本仓库人设 | 读取 `resources/persona.txt`；Paratera 专用 |
| `scripts/evaluation/evaluate_memory_reply.py` | 服务器；合成记忆回复评估 | 同上，不读取生产聊天 |
| `scripts/evaluation/evaluate_social.py` | 服务器；本仓库社交判断逻辑 | 使用 `plugins.deepark_companion.social`；Paratera 专用 |
| `scripts/evaluation/probe_embedding.py` | 服务器；SiliconFlow 合成 embedding 请求 | 读取服务器本地密钥文件 |
| `scripts/evaluation/verify_memory.py` | AstrBot 容器；embedding + 临时 FAISS 隔离验证 | 真实 API，依赖 LivingMemory 与云 embedding 配置 |

服务器工具中的 `/home/grainrain/astrbot`、容器工具中的 `/AstrBot` 是运行环境路径，本轮没有改成开发机路径。部分脚本仍在导入时运行，因此只做 AST 解析，不能用批量 import 检查。参数化与 main() 改造列入 [后续计划](plans/2026-10-28-repository-layout.md)。

运行人格评估时需保留整个仓库目录关系，不再依赖 `/tmp/deepark-persona.txt`。新路径下的在线工具尚未做真实调用验证。

## 转为集成测试

| 原路径 | 新路径 |
|---|---|
| `container_integration.py` | `tests/integration/test_adapter.py` |
| `container_batching.py` | `tests/integration/test_batching.py` |
| `container_public_profile.py` | `tests/integration/test_public_profile.py` |
| `container_participation.py` | `tests/integration/test_participation.py` |

四份文件均使用模拟发送/模型。修正导入和 patch 路径；旧的“清空 allow_groups 拒绝访问”测试改为清空原生白名单，符合已上线的授权行为。

## 删除的过期脚本（17 个）

| 原路径 | 清理依据 |
|---|---|
| `activate_group.py`、`authorize_current_group.py` | 写入已取消的 allow_groups；后者还写死群与模型配置 |
| `deploy_plugin.py` | 首次安装脚本，要求目标不存在，初始化过期授权配置 |
| `upgrade_plugin.py` | 依赖旧 `/tmp/deepark-adapter-test/plugin`；无明确版本输入 |
| `deploy_batching.py` | 固定旧批处理暂存目录并覆盖历史配置值 |
| `deploy_media.py` | 一次性创建已存在的 vision/ASR provider，再运行会断言失败 |
| `deploy_participation.py` | 断言旧 allow_groups，绑定已废弃授权结构和固定群 |
| `deploy_persona.py` | 首次人设设置流程，依赖旧临时输入并更改全局配置 |
| `deploy_public_profile.py` | 写死初次部署会话与 `/tmp/deepark-profile-tests/plugin` |
| `deploy_reply_tuning.py` | 一次性人格/回复配置调节，使用旧暂存代码与人设 |
| `deploy_social.py` | 固定旧社交部署配置，依赖旧暂存目录和 allow_groups |
| `ecosystem/activate.py`、`ecosystem/configure.py`、`ecosystem/deploy.py` | 已完成的第三方插件初始化流程；依赖一次性临时 API/tools/persona 文件，重跑会覆盖配置 |
| `ecosystem/api.py` | 上述已删除初始化脚本的唯一公共辅助文件，无剩余调用方 |
| `ecosystem/repair_session.py` | 针对当时平台前缀迁移的专项修复，无迁移时直接断言失败 |
| `benchmarks/backend.py` | 被保留的 backend_compare.py 覆盖；后者支持多 provider 与官方 DeepSeek |

另删除 `ecosystem/persona.txt`：删除前与根目录 `persona.txt` 字节完全一致；唯一维护副本迁至 `resources/persona.txt`。

没有把旧部署脚本包装成新的通用发布器，也没有删除服务器上的备份和 rollback.sh。维护中的人格回滚保留，因为它接受明确备份参数且只恢复人设行。

## 历史追溯

例如查看已删除的部署脚本：

```sh
git show 676d81d:deploy_participation.py
```

其他文件用原路径替换即可。恢复脚本不代表其适合当前生产；需重新审阅配置结构和副作用。历史报告保留当时文件名与命令，不把它们误写成当前可执行入口。
