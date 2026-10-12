from fastapi import FastAPI, HTTPException, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import edge_tts
from fastapi.responses import StreamingResponse
import traceback

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


@app.get("/health")
async def health():
    return {"ok": True, "version": "2.0.1"}


@app.post("/api/tts")
async def tts(req: TTSRequest):
    try:
        # 先收集完整音频，失败时返回真实错误（避免流式响应吞掉异常导致 200+空音频）
        communicate = edge_tts.Communicate(req.text, req.voice, rate=str(req.rate))
        audio_chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        if not audio_chunks:
            print("[tts] edge-tts returned no audio chunks")
            return JSONResponse(status_code=502, content={"detail": "edge-tts returned no audio"})

        total = sum(len(c) for c in audio_chunks)
        print(f"[tts] ok voice={req.voice} bytes={total}")

        async def gen():
            for c in audio_chunks:
                yield c

        return StreamingResponse(gen(), media_type="audio/mpeg")
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})