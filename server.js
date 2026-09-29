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
    
    // 告诉浏览器返回的是音频
    res.setHeader('Content-Type', 'audio/mpeg');
    // 把音频数据发回去
    res.send(result.audio);
  } catch (error) {
    console.error('TTS synthesis failed:', error);
    res.status(500).json({ error: 'Failed to synthesize speech' });
  }
});

// 启动服务
app.listen(port, () => {
  console.log(`TTS proxy server is running on port ${port}`);
});
