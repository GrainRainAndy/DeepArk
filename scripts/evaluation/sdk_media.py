"""Synthetic request through the installed AstrBot adapters, outside message dispatch."""
import asyncio
import json
from pathlib import Path
import struct
import zlib
from astrbot.core.provider.sources.openai_source import ProviderOpenAIOfficial
from astrbot.core.provider.sources.whisper_api_source import ProviderOpenAIWhisperAPI

async def main():
    config=json.loads(Path('/AstrBot/data/cmd_config.json').read_text(encoding='utf-8-sig'))
    vision=next(p for p in config['provider'] if p['id']=='deepark-vision')
    source=next(s for s in config['provider_sources'] if s['id']==vision['provider_source_id'])
    stt=next(p for p in config['provider'] if p['id']=='deepark-asr')
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    pixels=b''.join(b'\0'+b''.join(bytes((255,0,0) if x<48 else (0,0,255)) for x in range(96)) for y in range(64))
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',96,64,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')
    Path('/tmp/deepark-colors.png').write_bytes(png)
    visual=ProviderOpenAIOfficial({**source,**vision},config['provider_settings'])
    audio=ProviderOpenAIWhisperAPI(stt,config['provider_stt_settings'])
    try:
        response=await asyncio.wait_for(visual.text_chat(prompt='描述图片左右两半的颜色，只回答颜色。',image_urls=['/tmp/deepark-colors.png'],contexts=[],max_tokens=512,request_max_retries=1),60)
        print(json.dumps({'adapter':'vision','text':response.completion_text},ensure_ascii=False),flush=True)
        text=await asyncio.wait_for(audio.get_text('/tmp/deepark-synthetic.wav'),60)
        print(json.dumps({'adapter':'asr','text':text},ensure_ascii=False),flush=True)
    except Exception as exc:
        print(json.dumps({'error_type':type(exc).__name__}),flush=True)
        raise SystemExit(1)
    finally:
        await visual.terminate();await audio.terminate()

asyncio.run(main())
