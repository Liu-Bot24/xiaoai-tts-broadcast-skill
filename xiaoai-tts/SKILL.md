---
name: xiaoai-tts
description: Control Xiaoai speaker via OpenXiaoAI Voice API for high-quality TTS playback. Use when the user wants to play voice notifications, announcements, or TTS through the Xiaoai speaker using the OpenXiaoAI HTTP API. Supports Doubao (ByteDance) TTS with emotions, voice types, and speed control. Triggers on queries like "小爱播报", "语音播报", "让小爱说", "读出来", "播报"， "xiaoai-tts"，"tts", "TTS", "小爱音箱语音播报".
---

# XiaoAI TTS

通过 XiaoAI HTTP API 控制小爱音箱播放语音，支持火山引擎豆包 TTS 多情感、多音色、语速调整等高级功能。

## 前置配置

在 env 中添加：

```bash
OPENXIAOAI_BASE_URL="http://192.168.x.x:9092"  # OpenXiaoAI 服务地址
```

## 使用方法

```bash
# 语音播报（优先 Doubao TTS，失败自动回退小爱自带 TTS）
xiaoai-tts tts "你好，我是小爱语音助手"

# 指定音色
xiaoai-tts tts "你好" -s zh_female_vv_uranus_bigtts

# 调整语速（0.8-2.0）
xiaoai-tts tts "你好" --speed 1.2

# 指定情感（仅多情感音色支持）
xiaoai-tts tts "你怎么能这样！" -s zh_male_lengkugege_emo_v2_mars_bigtts -m angry

# 2.0 音色 + 上下文指令
xiaoai-tts tts "这是一个很长的句子" -s zh_female_vv_uranus_bigtts -c "你可以说慢一点吗？"

# 强制使用小爱自带 TTS
xiaoai-tts text "你好"

# 长文本分段顺序播报（适合小说、文章、飞书粘贴的大段文本）
xiaoai-tts broadcast "从前有一座山..."
cat story.txt | xiaoai-tts broadcast --stdin
xiaoai-tts broadcast --file story.txt

# 有状态播报模式（适合飞书等非小爱频道）
xiaoai-tts mode on --scope feishu-default
xiaoai-tts mode off --scope feishu-default
xiaoai-tts mode status --scope feishu-default
xiaoai-tts handle "启动小爱播报模式" --scope feishu-default
xiaoai-tts handle "要播报的正文" --scope feishu-default
xiaoai-tts handle "退出播报模式" --scope feishu-default

# 唤醒小爱
xiaoai-tts wakeup
xiaoai-tts wakeup --silent   # 静默唤醒

# 状态 / 健康检查
xiaoai-tts status
xiaoai-tts health

# 播放音频
xiaoai-tts file /path/to/audio.mp3
xiaoai-tts url "http://example.com/audio.mp3"

# 查看可用音色
xiaoai-tts voices            # 所有音色
xiaoai-tts voices -v 2.0     # 仅 2.0 音色
xiaoai-tts voices -v 1.0     # 仅 1.0 音色
```

## 播报模式

播报模式是硬状态，状态保存在运行本 Skill 的机器本地文件中：

- 默认路径：`~/.xiaoai-tts/broadcast_state.json`
- 可用环境变量 `XIAOAI_TTS_STATE_PATH` 覆盖。
- `--scope` 用于隔离不同聊天、群聊或用户；如果能拿到飞书 chat id / open id / session id，必须作为 scope。拿不到时使用 `feishu-default`。

当用户要求"启动小爱播报模式"、"进入小爱朗读模式"、"下面这段用小爱读出来"时，调用：

```bash
xiaoai-tts handle "启动小爱播报模式" --scope <stable-feishu-scope>
```

当用户发送"退出播报模式"、"停止播报模式"、"不用读了"时，调用：

```bash
xiaoai-tts handle "退出播报模式" --scope <stable-feishu-scope>
```

在播报模式开启后，用户后续发送的正文应原样作为播报内容，不要摘要、改写或续写。对每条可能来自飞书播报会话的消息，调用：

```bash
xiaoai-tts handle "<用户原文>" --scope <stable-feishu-scope>
```

文本很长时优先通过 stdin 或临时 UTF-8 文本文件传入，避免 shell 参数过长：

```bash
cat /path/to/message.txt | xiaoai-tts handle --stdin --scope <stable-feishu-scope>
```

`handle` 会自己判断：

- 收到启动指令：打开该 scope 的播报模式，不播报启动指令本身。
- 收到退出指令：关闭该 scope 的播报模式，不播报退出指令本身。
- 该 scope 已开启：把正文转发给小爱音箱分段播报。
- 该 scope 未开启：忽略正文，不调用小爱音箱。

这意味着播报模式不依赖 Agent 的上下文记忆；只要 Agent 对飞书消息调用 `handle` 并传入同一个 scope，状态就会稳定生效。

如果用户同时要求生成内容并播报，可以先生成适合朗读的纯文字，再调用 `xiaoai-tts broadcast` 或 `xiaoai-tts handle --force`；不要默认限制为短回复。

## 常用音色推荐

### 用户自定义声音复刻（`S_` 前缀）

如果用户想使用自定义复刻音色，引导用户前往 [火山引擎声音复刻控制台](https://console.volcengine.com/speech/new/experience/clone) 上传声音训练专属音色，训练完成后在 [音色库](https://console.volcengine.com/speech/new/voices?projectName=default) 的「我的音色」中复制音色 ID（格式为 `S_xxxxxxxx`），填入 `-s` 参数即可使用。

```bash
xiaoai-tts tts "你好，我是你的专属语音助手" -s S_xxxxxxxx
```

> 注意：声音复刻音色 ID 通常以 `S_` 开头，传入时无需通过 `xiaoai-tts voices` 列表验证，直接使用即可。

**工作流：**
1. 用户想使用自定义复刻音色时，引导用户前往火山引擎完成声音训练并获取音色 ID
2. 用户拿到音色 ID 后，引导用户将音色昵称和 ID 填入下方表格
3. 后续用户提到音色昵称时，直接从表格中查找对应 ID 使用

### 用户已保存的自定义音色

| 音色名称 | speaker_id | 特点 |
|---------|------------|------|
| （暂无，引导用户添加） | - | - |

### 2.0 音色（推荐）
| 音色名称 | speaker_id | 特点 |
|---------|------------|------|
| Vivi 2.0 | zh_female_vv_uranus_bigtts | 通用场景，情感变化 |
| 小何 2.0 | zh_female_xiaohe_uranus_bigtts | 通用场景 |
| 云舟 2.0 | zh_male_m191_uranus_bigtts | 通用场景 |
| 小天 2.0 | zh_male_taocheng_uranus_bigtts | 通用场景 |

### 1.0 音色（多情感）
| 音色名称 | speaker_id | 特点 |
|---------|------------|------|
| 冷酷哥哥 | zh_male_lengkugege_emo_v2_mars_bigtts | 支持 emotion 参数 |
| 高冷御姐 | zh_female_gaolengyujie_emo_v2_mars_bigtts | 支持 emotion 参数 |
| 灿灿 | zh_female_cancan_mars_bigtts | 通用场景 |
| 爽快思思 | zh_female_shuangkuaisisi_moon_bigtts | 通用场景 |

## 情感参数（仅多情感音色）

| 中文情感 | 英文参数 | 说明 |
|---------|----------|------|
| 开心 | happy | 愉快语气 |
| 悲伤 | sad | 悲伤语气 |
| 生气 | angry | 愤怒语气 |
| 惊讶 | surprised | 惊讶语气 |
| 撒娇 | lovey-dovey | 撒娇语气 |
| 温柔 | tender | 温柔语气 |
| 讲故事 | storytelling | 讲故事语气 |
| 新闻播报 | news | 新闻播报语气 |
| 广告营销 | advertising | 广告营销语气 |
| 磁性 | magnetic | 磁性声音 |

完整情感列表参考：`xiaoai-tts voices`

## API 端点

- Base URL: `http://{host}:9092`
- Content-Type: `application/json`
```
