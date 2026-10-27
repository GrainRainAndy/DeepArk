"""Bounded semantic validation for implicit replies when group messages arrive."""
import asyncio
import json
import time
from astrbot.api import logger
from . import social


async def still_relevant(plugin, event, candidate):
    scope=event.unified_msg_origin
    if not plugin.participation_still_valid(event):return False
    initial=event.get_extra('deepark_participation_snapshot',0)
    checked=event.get_extra('deepark_relevance_checked',initial)
    while True:
        history=plugin.store.history(scope,time.time())
        new=[x for x in history if x['at']>checked]
        if not new:return True
        if any(x['subject']=='@bot' for x in new):
            logger.info('deepark participation skip: newer_bot_reply')
            return False
        if all(social.is_noise(x['text']) for x in new):
            event.set_extra('deepark_relevance_checked',new[-1]['at'])
            return True
        calls=event.get_extra('deepark_relevance_calls',0)
        if calls>=2 or time.time()-initial>90:
            logger.info('deepark participation skip: relevance_window_exhausted')
            return False
        if not plugin.store.reserve_followup_probe(scope,time.time(),min_gap=0):
            logger.info('deepark participation skip: decision_hourly_budget')
            return False
        event.set_extra('deepark_relevance_calls',calls+1)
        payload={'original_context':[x for x in history if x['at']<=initial][-8:], 'candidate_reply':candidate,'new_messages':new}
        try:
            raw=await asyncio.wait_for(plugin.generate(scope,json.dumps(payload,ensure_ascii=False),social.RELEVANCE_PROMPT,180,provider_id=plugin.config.get('decision_provider_id','deepark-decision')),timeout=8)
            keep=social.keep_reply(raw)
        except Exception as exc:
            logger.info('deepark participation skip: relevance_error_%s',type(exc).__name__)
            return False
        if not keep:
            logger.info('deepark participation skip: semantic_stale')
            return False
        if not plugin.participation_still_valid(event):return False
        checked=new[-1]['at']
        event.set_extra('deepark_relevance_checked',checked)
        # Re-check messages arriving during this await; at most two model calls.
