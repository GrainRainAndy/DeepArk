# 话题上下文插件（待验收）

本轮只在服务器独立 checkout 开发，没有部署或修改生产配置。
源码位于 `plugins/deepark_topic_context/`；算法、预算、配置和局限详见该目录 README。
现有 companion 增加可选协作接口，新插件不可用时保留原有流程。

## 用户离线验收

在独立 checkout 根目录激活 Python 3.12.15 / AstrBot 4.29.3 测试环境，然后执行以下命令。

```sh
git rev-parse HEAD
python3 -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/integration -t . -v
python -m plugins.deepark_topic_context.replay
```

回放只用手工标注的合成消息，没有外部模型调用或 QQ 发送。观察：

1. 前两句建立 squad 主话题。
2. 第三句 tea 插话保留，但主话题仍为 squad。
3. 第四句模拟被 @ 回答茶问题，addressed_id 有值，主话题不变。
4. 第五句回到 squad；之后持续讨论 dinner，达到证据阈值后切换。
5. metrics 显示人数、频率、上下文预算和插话权重随活动变化。

这些结果验证状态机，不等于验证真实模型的语义准确率。真实模型评测
需要另行约定合成案例、请求规模及费用；真实 QQ 验收还需目标会话、
动作和窗口授权。本轮不执行这两类验证。

## 配置与发布边界

默认禁用，默认授权会话为空，模型 ID 为空；仅安装也不会开始话题判断。
启用后会对已授权群调用指定分类模型，受每群与全局预算、超时限制。
不自行发送消息，是否参与沿用 companion 权限与节奏控制。

用户测试、代码审阅、合并和生产发布分别进行。若未来采用，需备份受影响
的 companion 代码和插件配置；本变更无数据库迁移，回退不恢复聊天数据库。
验收时记录实际提交和测试结果。
