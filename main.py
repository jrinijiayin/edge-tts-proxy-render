from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import edge_tts
import edge_tts.communicate as comm
from edge_tts.constants import TRUSTED_CLIENT_TOKEN
import traceback
import asyncio

# 微软新服务器（2026 年微软更换端点，edge-tts 旧端点 speech.platform.bing.com 已全局 403；
# 社区 FluentVoice 验证新端点 api.msedgeservices.com 全部音色可用）
comm.WSS_URL = "wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1?Ocp-Apim-Subscription-Key={}".format(TRUSTED_CLIENT_TOKEN)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-AriaNeural"
    rate: float = 1.0


def fmt_rate(r: float) -> str:
    """把前端数值语速(1=正常,1.2=快20%)转成 edge-tts 需要的 +N% 格式"""
    if r <= 0:
        return "+0%"
    return f"{(r - 1) * 100:+.0f}%"


async def synth_once(req: TTSRequest):
    c = edge_tts.Communicate(req.text, req.voice, rate=fmt_rate(req.rate))
    chunks = []
    async for ch in c.stream():
        if ch["type"] == "audio":
            chunks.append(ch["data"])
    return chunks


@app.get("/health")
async def health():
    return {"ok": True, "version": "3.0.0", "endpoint": "api.msedgeservices.com"}


@app.post("/api/tts")
async def tts(req: TTSRequest):
    last_err = None
    for attempt in range(4):
        try:
            chunks = await synth_once(req)
            if not chunks:
                print(f"[tts] no audio voice={req.voice} attempt={attempt + 1}")
                return JSONResponse(status_code=502, content={"detail": "edge-tts returned no audio"})
            total = sum(len(c) for c in chunks)
            print(f"[tts] ok voice={req.voice} bytes={total} attempt={attempt + 1}")

            async def gen():
                for c in chunks:
                    yield c

            return StreamingResponse(gen(), media_type="audio/mpeg")
        except Exception as e:
            last_err = str(e)
            print(f"[tts] fail voice={req.voice} attempt={attempt + 1} err={str(e)[:120]}")
            # 429 限流：等待后重试
            if "429" in str(e) and attempt < 3:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            break
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": last_err})