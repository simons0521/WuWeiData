import asyncio
import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

app = FastAPI(title="FastAPI Streaming Demo")


# ---------- 1. 普通文本流：逐字输出（类似 ChatGPT 打字效果） ----------
async def text_generator(text: str, delay: float = 0.1):
    for ch in text:
        yield ch
        await asyncio.sleep(delay)


@app.get("/stream/text")
async def stream_text(msg: str = "你好，这是一个 FastAPI 流式输出演示！"):
    return StreamingResponse(
        text_generator(msg),
        media_type="text/plain; charset=utf-8",
    )


# ---------- 2. SSE（Server-Sent Events）：按事件推送 ----------
async def sse_generator(count: int):
    for i in range(1, count + 1):
        data = json.dumps({"index": i, "message": f"第 {i} 条消息"}, ensure_ascii=False)
        yield f"data: {data}\n\n"  # SSE 格式：以 data: 开头，空行结束
        await asyncio.sleep(1)
    yield "event: done\ndata: 完成\n\n"


@app.get("/stream/sse")
async def stream_sse(count: int = 5):
    return StreamingResponse(
        sse_generator(count),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------- 3. 演示页面 ----------
HTML = """
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <title>FastAPI 流式演示</title>
  <style>
    body { font-family: sans-serif; max-width: 640px; margin: 40px auto; }
    pre { background: #f4f4f4; padding: 12px; min-height: 60px; white-space: pre-wrap; }
    button { margin-right: 8px; padding: 6px 14px; }
  </style>
</head>
<body>
  <h2>FastAPI 流式 API 演示</h2>
  <button onclick="startText()">文本流 (fetch)</button>
  <button onclick="startSSE()">SSE (EventSource)</button>
  <pre id="out"></pre>

  <script>
    const out = document.getElementById("out");

    // 方式一：fetch + ReadableStream 读取文本流
    async function startText() {
      out.textContent = "";
      const res = await fetch("/stream/text");
      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        out.textContent += decoder.decode(value, { stream: true });
      }
    }

    // 方式二：EventSource 接收 SSE
    function startSSE() {
      out.textContent = "";
      const es = new EventSource("/stream/sse?count=5");
      es.onmessage = (e) => { out.textContent += e.data + "\\n"; };
      es.addEventListener("done", (e) => { out.textContent += "[" + e.data + "]\\n"; es.close(); });
      es.onerror = () => es.close();
    }
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("stream_api:app", host="127.0.0.1", port=8000, reload=True)