---
name: xiaoai-tts
description: Use this OpenClaw skill to broadcast text through XiaoAI speakers via Open-XiaoAI Bridge. Trigger it for 小爱播报, 小爱朗读, 读出来, 语音播报, Feishu broadcast mode, 启动/开启/进入小爱播报模式, 退出/停止/关闭播报模式, and every later Feishu/chat message while broadcast mode may be active. Stateful Feishu/chat broadcast mode must call `xiaoai-tts handle`, not `broadcast`.
---

# XiaoAI TTS Broadcast

This skill sends text from OpenClaw to XiaoAI speakers through the Open-XiaoAI Bridge HTTP API.

## Required Environment

The OpenClaw runtime must have:

```bash
OPENXIAOAI_BASE_URL="http://<bridge-host>:9092"
```

For this user's bridge, the expected value is:

```bash
OPENXIAOAI_BASE_URL="http://192.168.6.237:9092"
```

Use Python 3.8 or newer. On native Windows, call `xiaoai-tts.cmd` if `xiaoai-tts` is not available.

## Commands

Health check:

```bash
xiaoai-tts health
```

Short text with XiaoAI native TTS:

```bash
xiaoai-tts text "这是一条播报测试。" --blocking
```

Long text:

```bash
xiaoai-tts broadcast --file story.txt
cat story.txt | xiaoai-tts broadcast --stdin
```

Stateful broadcast mode:

```bash
xiaoai-tts handle "启动小爱播报模式" --scope feishu-default
xiaoai-tts handle "要播报的正文" --scope feishu-default
xiaoai-tts handle "退出播报模式" --scope feishu-default
```

## Broadcast Mode Contract

Always use `xiaoai-tts handle` for Feishu/chat broadcast mode.

When the user says any start command such as "启动小爱播报模式", "开启播报模式", "/小爱播报", or "下面这段用小爱读出来", call:

```bash
xiaoai-tts handle "<用户原文>" --scope <stable-chat-scope>
```

When the user says any stop command such as "退出播报模式", "停止小爱播报模式", "不用读了", or "/退出小爱播报", call the same command form:

```bash
xiaoai-tts handle "<用户原文>" --scope <stable-chat-scope>
```

After broadcast mode has been started, every later Feishu/chat message from the same conversation must also be passed to:

```bash
xiaoai-tts handle "<用户原文>" --scope <stable-chat-scope>
```

Use the same scope for start, body messages, and stop. Prefer Feishu chat id, open id, or OpenClaw session id. If no stable id is available, use `feishu-default`.

For long messages, use stdin or a UTF-8 file:

```bash
cat /path/to/message.txt | xiaoai-tts handle --stdin --scope <stable-chat-scope>
```

`handle` is the state machine:

- Start command: turns mode on and does not broadcast the command itself.
- Stop command: turns mode off and does not broadcast the command itself.
- Mode on: forwards the message to XiaoAI in ordered chunks.
- Mode off: ignores ordinary messages.

Do not use `xiaoai-tts mode on` alone for Feishu broadcast mode; it only flips state and does not make future messages enter this skill. Do not use `xiaoai-tts broadcast` for stateful mode; it bypasses start/stop handling.

## Direct Forwarding

Use `broadcast` or `handle --force` only when the user explicitly asks to read a specific text immediately and no persistent mode is needed:

```bash
xiaoai-tts handle "请直接读这段文字" --force --scope feishu-default
```
