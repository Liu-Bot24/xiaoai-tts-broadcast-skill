# OpenClaw Operator Guide

This guide is for the OpenClaw Agent or operator that wires Feishu/chat messages into the Skill.

## Routing Rule

For Feishu broadcast mode, route every relevant Feishu/chat message to:

```bash
xiaoai-tts handle "<original-message-text>" --scope "<stable-chat-scope>"
```

Use the same `scope` for start commands, body messages, and stop commands. Prefer Feishu chat id, open id, or OpenClaw session id. If none is available, use:

```bash
--scope feishu-default
```

## Start And Stop

Start examples:

```text
启动小爱播报模式
开启播报模式
/小爱播报
下面这段用小爱读出来
```

Stop examples:

```text
退出播报模式
停止小爱播报模式
不用读了
/退出小爱播报
```

Do not only call `xiaoai-tts mode on`. That flips state but does not ensure later Feishu messages keep entering this Skill.

Do not use `xiaoai-tts broadcast` for stateful Feishu mode. Use `handle`, because `handle` detects start and stop commands.

## Long Messages

When the message is long, pass it through stdin or a UTF-8 temporary file:

```bash
cat /path/to/message.txt | xiaoai-tts handle --stdin --scope "<stable-chat-scope>"
```

## Verification

```bash
xiaoai-tts health
xiaoai-tts handle "启动小爱播报模式。" --scope feishu-default --dry-run --json
xiaoai-tts handle "退出播报模式。" --scope feishu-default --dry-run --json
```

`--dry-run` must not change the saved broadcast state.
