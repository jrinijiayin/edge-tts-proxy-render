const express = require('express');
const cors = require('cors');
const { EdgeTTS } = require('edge-tts-universal');

const app = express();
const port = process.env.PORT || 3000;

// 允许所有跨域请求（方便前端调用）
app.use(cors());
// 解析前端发来的 JSON 数据
app.use(express.json());

// 接收前端 POST 请求 /api/tts
app.post('/api/tts', async (req, res) => {
  const { text, voice } = req.body;
  
  if (!text) {
    return res.status(400).json({ error: 'Text is required' });
  }

  try {
    // 调用 Edge TTS 获取语音，voice 默认用美式女声 Aria
    const tts = new EdgeTTS(text, voice || 'en-US-AriaNeural');
    const result = await tts.synthesize();
    
    // 1. 关键检查：如果音频数据为空，打印日志并报错，方便定位
    if (!result.audio || result.audio.length === 0) {
      console.error('>>> 严重警告：合成的音频长度为 0！可能是微软接口屏蔽了 Render 的服务器 IP。');
      return res.status(500).json({ error: 'Empty audio generated' });
    }

    // 2. 关键：强制转换成 Buffer，并明确告诉浏览器数据长度
    const audioBuffer = Buffer.from(result.audio);
    res.setHeader('Content-Type', 'audio/mpeg');
    res.setHeader('Content-Length', audioBuffer.length); // 帮前端正确解析 Blob 大小
    
    // 3. 发送音频数据
    res.send(audioBuffer);

  } catch (error) {
    console.error('TTS synthesis failed:', error);
    // 把详细的错误信息返回给前端，方便你在 F12 里看到原因
    res.status(500).json({ 
      error: 'Failed to synthesize speech', 
      details: error.message 
    });
  }
});

// 启动服务
app.listen(port, () => {
  console.log(`TTS proxy server is running on port ${port}`);
});
