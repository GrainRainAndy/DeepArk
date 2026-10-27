"""Reversible AstrBot 4.29.3 ProcessStage bridge; only opted-in private sessions."""
from contextlib import aclosing
import copy
import time
from types import SimpleNamespace
from astrbot.api import logger,sp
from astrbot.core.message.components import Plain
from astrbot.core.star.filter.command import CommandFilter
from astrbot.core.star.filter.command_group import CommandGroupFilter
from astrbot.core.star.filter.regex import RegexFilter
from .batching import TurnBuffer

class BatchBridge:
    def __init__(self,plugin):
        self.plugin=plugin
        def value(key,default,lo,hi):
            try:return max(lo,min(hi,float(plugin.config.get(key,default))))
            except (ValueError,TypeError):return default
        self.buffer=TurnBuffer(quiet=value('batch_quiet_seconds',1.5,.1,3),maximum=value('batch_max_seconds',4,1,8))
        self.target=None;self.original=None;self.wrapper=None

    async def eligible(self,event):
        cfg=self.plugin.config
        if not cfg.get('enabled',True) or not cfg.get('batching_enabled',False):return False
        if event.get_group_id() or event.get_platform_name()!='aiocqhttp':return False
        if event.plugins_name is not None and 'deepark_companion' not in event.plugins_name:return False
        if event.unified_msg_origin not in cfg.get('batching_sessions',[]):return False
        if str(event.get_sender_id())==str(event.get_self_id()):return False
        if not event.is_at_or_wake_command or event.is_stopped():return False
        native=self.plugin.context.get_config(event.unified_msg_origin)
        plugins=native.get('plugin_set',['*'])
        if '*' not in plugins and 'deepark_companion' not in plugins:return False
        prefs=await sp.get_async(scope='umo',scope_id=event.unified_msg_origin,key='session_plugin_config',default={}) or {}
        return 'deepark_companion' not in prefs.get(event.unified_msg_origin,{}).get('disabled_plugins',[])

    def command(self,event):
        # Respect already-matched native command/regex handlers, including unprefixed commands.
        matched=any(isinstance(f,(CommandFilter,CommandGroupFilter,RegexFilter)) for h in (event.get_extra('activated_handlers') or []) for f in h.event_filters)
        return matched or event.get_message_str().lstrip().startswith('/')

    def install(self,target=None):
        if target is None:
            from astrbot.core.pipeline.process_stage.stage import ProcessStage
            target=ProcessStage
        if self.target is not None:return
        self.target=target;self.original=target.process
        original=self.original;bridge=self
        async def wrapped(stage,event):
            eligible=await bridge.eligible(event)
            if eligible and bridge.command(event):
                reset=any(isinstance(f,CommandFilter) and f.command_name in {'reset','new','stop'} for h in (event.get_extra('activated_handlers') or []) for f in h.event_filters)
                if reset:await bridge.buffer.discard_pending(event.unified_msg_origin+'|'+str(event.get_sender_id()))
            if not eligible or bridge.command(event):
                async with aclosing(original(stage,event)) as stream:
                    async for result in stream:yield result
                return
            text=event.get_message_str()
            parts=event.message_obj.message
            merge=bool(text.strip()) and bool(parts) and all(isinstance(p,Plain) for p in parts)
            # Full UMO plus authenticated sender: never merge identities.
            key=event.unified_msg_origin+'|'+str(event.get_sender_id())
            turn=await bridge.buffer.enter(key,event,merge,len(text))
            if turn is None:
                event.set_extra('deepark_batch_absorbed',True);event.stop_event();return
            start=time.monotonic()
            try:
                items=turn.items
                if len(items)>1:
                    combined='\n'.join(item.get_message_str() for item in items)
                    event.message_obj=copy.copy(event.message_obj)
                    event.message_obj.message=[Plain(combined)]
                    event.message_obj.message_str=combined
                    event.message_str=combined
                native=bridge.plugin.context.get_config(event.unified_msg_origin)
                access=native.get('platform_settings',{})
                wl={str(x).strip() for x in access.get('id_whitelist',[]) if str(x).strip()}
                exempt=event.is_admin() and access.get('wl_ignore_admin_on_friend',False)
                service=await sp.get_async(scope='umo',scope_id=event.unified_msg_origin,key='session_service_config',default={}) or {}
                if (access.get('enable_id_white_list') and wl and event.unified_msg_origin not in wl and not exempt) or service.get('session_enabled') is False or service.get('llm_enabled') is False:
                    event.stop_event();return
                if len(items)>1 and native.get('content_safety'):
                    from astrbot.core.pipeline.content_safety_check.stage import ContentSafetyCheckStage
                    checker=ContentSafetyCheckStage()
                    await checker.initialize(SimpleNamespace(astrbot_config=native))
                    async with aclosing(checker.process(event)) as checks:
                        async for result in checks:yield result
                    if event.is_stopped():return
                event.set_extra('deepark_batch_count',len(items))
                event.set_extra('deepark_batch_message_ids',[str(x.message_obj.message_id) for x in items])
                event.set_extra('enable_streaming',False)
                logger.info('deepark batch start: messages=%d wait=%.3fs',len(items),turn.waited)
                async with aclosing(original(stage,event)) as stream:
                    async for result in stream:yield result
            finally:
                await bridge.buffer.finish(turn)
                logger.info('deepark batch finished: native_and_send=%.3fs',time.monotonic()-start)
        self.wrapper=wrapped;target.process=wrapped
        logger.info('deepark short-message batching installed: quiet=%.1fs max=%.1fs',self.buffer.quiet,self.buffer.maximum)

    async def close(self):
        if self.target is not None and self.target.process is self.wrapper:self.target.process=self.original
        await self.buffer.close()
