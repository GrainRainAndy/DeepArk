# 社区插件接入

用户授权：参考大肥鱼persona调整deepark；引入LivingMemory+硅基流动云embedding、meme_manager、qzone、qqprofile、proactive_chat。不新增语音功能。

执行顺序：全量备份；安装指定五插件并检查版本/schema；验证SF BAAI/bge-m3；修改persona及文本分段；设置LivingMemory为唯一长期记忆入口，保留群参与决策；表情包导入与低频触发；QQ空间/资料工具仅管理员按需使用，自动发布关闭；主动私聊仅已有主人会话，群调度不重复；离线/API检查与最终健康检查。

不运行参考包一键脚本，不安装其语音、唱歌及签名附加插件。密钥只在服务器配置及受限临时文件中使用，不打印。安装/测试不发布说说、不改资料、不主动发送测试消息。CPU服务器不加载本地embedding、TTS或视觉模型。

已备份：/home/grainrain/astrbot-backups/ecosystem-20261027T075347Z/astrbot-data.tar.gz，SHA256 8a40d2ed955f12f4e8ba2884f1448866cd1a07e362f8e4866cb6ca8b388b2b97。
