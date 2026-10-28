> 历史资料：保留当时路径、命令和状态；当前操作请见 [运维说明](../OPERATIONS.md)，旧脚本去向见 [清理清单](../SCRIPT_INVENTORY.md)。

> 历史阶段记录：其中状态、测试数字及授权只描述当时工作，不是当前操作授权。当前入口见 [OPERATIONS.md](../OPERATIONS.md) 和 [基线记录](BASELINE.md)。

# deepark 社区插件整合（2026-10-27）

已部署到 aliyun-ecs，AstrBot 4.29.3。原完整数据备份：
`/home/grainrain/astrbot-backups/ecosystem-20261027T075347Z/astrbot-data.tar.gz`
SHA256 `8a40d2ed955f12f4e8ba2884f1448866cd1a07e362f8e4866cb6ca8b388b2b97`。
配置/人设/companion代码二次备份：
`/home/grainrain/astrbot-backups/ecosystem-config-20261027T080304Z`。

## 实际配置

- persona：参考大肥鱼的短句、换行、固定性格偏好与语气示例，保留 deepark 女性 AI 舟友定位，活泼适度嘴欠；不套用主人/恋爱/鲸鱼设定。主文件 `../persona.txt` 与 `persona.txt` 一致。
- LivingMemory 2.7.3：唯一长期记忆入口；原 companion 长期记忆注入和提取停止，原数据保留。最近窗口50条、每10轮整理；会话和人格隔离，完整 UMO 白名单。管理员可用遗忘工具归档记忆；**归档是软删除，不等于物理清除**。管理入口为插件页面和 `/lmem help`。
- embedding：硅基流动 `BAAI/bge-m3`，1024维，provider `deepark-memory-sf`；模型推理在云端，本机CPU维护SQLite/FAISS/图索引。密钥来自本机 `deepark/.env` 的 SF_KEYS，首个可用 key，临时传输文件已删除。不是自动轮换密钥池。
- meme_manager 5.2.9：DeepSeek二创包1.0.0，174张/13分类；上限每条1张、概率35%，语义embedding/额外情绪LLM/自动收图关闭；base64发送兼容独立NapCat容器。本地存图，不配置外部图床。官方索引在服务器Raw连接重置，通过本机获取官方索引、服务器codeload下载完成。
- qzone v3.1.3：已关联登录账号，全部14个直接命令和两个LLM工具限管理员；自动发布/评论/阅读触发关闭。自然语言操作需明确管理员指令。不测试发布、点赞、评论。
- qqprofile v1.1.6：头像、昵称、签名、在线状态工具可用且管理员限定；自动同步人格名关闭；切换/列出人格工具同样设管理员且不加入deepark工具名单。不测试修改资料。
- proactive_chat v1.2.6：只在现有已授权私聊启用。自动触发等待120分钟，调度间隔120–480分钟，**北京时间04:00–09:00免主动打扰**，连续1条未回复即暂停。主动提示不催回、不撒娇、不编造浏览经历。TTS、遥测、外部通知、独立Web服务关闭。
- 群主动聊天尚未启用：当前仍缺目标群授权，原参与决策逻辑保留，新插件群调度关闭，避免重叠。未改变现有群白名单。
- companion v0.3.0：兼容LivingMemory保留原生上下文；动态工具白名单，普通成员仅记忆工具，管理员额外空间/资料工具，隐式接话不提供对外操作工具。原生active_reply关闭。
- 没有新增语音模型或TTS，原已有识图/ASR配置保持。

## 验证

34个本地回归测试、26个真实AstrBot SDK测试通过。`verify_memory.py` 使用云embedding和临时FAISS库验证写入、语义召回、跨会话排除、非白名单拒绝；合成数据没有写入正式记忆，也没有发送QQ消息。
正式LivingMemory状态索引ready；表情包文件计数检查完成；Qzone只读状态ready且bound=true。

## 维护与回退

WebUI可分别调整每个插件。停用proactive_chat可立刻停止这条主动私聊链路；不会影响正常回复。删除记忆需区分归档、永久删除和原始对话历史，不能承诺一次遗忘抹除所有副本。
恢复整包备份会回退此后聊天与记忆，应先备份当前data，再停AstrBot后恢复；不要在运行中覆盖数据库。NapCat不需随AstrBot重启。

脚本记录了本次部署步骤，不是一键重复执行器：configure.py需要一次性临时密钥；activate.py默认尝试在线拉索引，服务器Raw受限时使用已验证的本机索引缓存路径。
