# Agent参与判断 v0.2

按用户2026-10-27最新要求：识别未@的接话，参考公开项目兴趣度，由模型决定是否参与。

参考公开作者实现：
- https://github.com/Him666233/astrbot_plugin_group_chat_enhanced ：兴趣阈值/专注状态思路，项目已归档，不直接安装。
- https://github.com/chengzhi-c/astrbot_plugin_self_initiated_reply ：判断模型和AstrBot主回复管线分工。
- https://github.com/Mai-with-u/MaiBot ：群聊参与/回复意愿的架构参考；未声称复制其当前算法。

独立决策器输出action及addressed/interest/value/interruption。接话需要明确对机器人说，不要求高兴趣；主动插话/开题需要兴趣和价值较高、打扰风险低。代码只接收白名单动作和合法分数，模型不能扩展权限。没有固定舟关键词触发，也不因引用机器人自动回复。直接@仍用原生流程。

接话默认窗口120秒，一轮最多3次（最长10分钟），至少间隔5秒；绕过3分钟机器人安静期及10分钟主动尝试冷却。回复其他成员不能伪装成接话。隐式接话与插话走原生Agent生成，保留记忆hook；生成后再次检查静音、开关、权限和话题是否变化。

决策探测每群最多30次/小时、至少间隔5秒；15秒超时跳过。独立deepark-decision provider复用同一DeepSeek及原source，thinking.disabled、max_tokens700；不改主聊天模型参数。当前原生适配器会忽略text_chat的普通max_tokens kwargs，所以采用provider custom_extra_body保证决策预算实际传到API。

测试：34项本地+24项容器集成通过，包含agent选择skip、引用其他人、接话绕过长冷却、生成后静音/禁用取消。真实合成模型探针发现人格混用导致过度接话，已隔离提示词并明确机器人身份；非思考探针支持该参数，reasoning_tokens为0。服务延迟0.84–20.35秒不等，超过运行时15秒将跳过；不能用离线探针成功声称实时全成功。模型偶尔输出addressed布尔值，按0/1兼容，其余分数仍严格验证。

生产部署备份：`/home/grainrain/astrbot-backups/social-20261027T070518Z`，包含原主配置、插件配置、代码和rollback.sh。部署保留groups=0/proactive=false/dry_run=true；目标群仍未确认，不产生群测试消息。

生产SDK探针：首轮15秒请求超时；第二次1.69秒返回skip，确认provider实际可调用但追问判断仍有漏判，不能声称语义识别稳定。独立合成HTTP探针曾对相同类型追问返回followup。群中需观察误接/漏接，当前未向真实群发消息。
