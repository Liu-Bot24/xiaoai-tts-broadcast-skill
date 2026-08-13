---
name: xiaoai-tts
description: Broadcast text through a XiaoAI speaker via Open-XiaoAI Bridge. Use for 小爱播报, 小爱朗读, 读出来, 语音播报, starting or stopping XiaoAI broadcast mode, and every later message in a chat whose broadcast mode may be active.
metadata:
  {
    "openclaw":
      {
        "requires":
          {
            "anyBins": ["python3", "python", "py"],
            "env": ["OPENXIAOAI_BASE_URL"],
          },
      },
  }
---

# XiaoAI TTS Broadcast

Use this skill to send text to a XiaoAI speaker through Open-XiaoAI Bridge.

## Mandatory safe invocation

For stateful chat broadcast mode, pass every relevant message to `handle`. Keep the command string static and put the exact message and conversation scope in the exec tool's `env` object.

Use the first available Python command:

- Linux/macOS: `python3 "{baseDir}/tools/xiaoai-tts" handle --from-env --json`
- Alternative: `python "{baseDir}/tools/xiaoai-tts" handle --from-env --json`
- Windows with the Python Launcher: `py -3 "{baseDir}/tools/xiaoai-tts" handle --from-env --json`

Call the exec tool with fields equivalent to:

```json
{
  "command": "python3 \"{baseDir}/tools/xiaoai-tts\" handle --from-env --json",
  "env": {
    "XIAOAI_TTS_MESSAGE": "<exact current message>",
    "XIAOAI_TTS_SCOPE": "<stable conversation id>"
  }
}
```

Never interpolate the message or scope into `command`, even after quoting or escaping it. Never invoke a `.cmd` file with message text. The `env` values are data, not shell syntax.

Use the same stable scope for start commands, ordinary messages, and stop commands. Prefer the channel chat ID, sender ID, or OpenClaw session ID. Use `feishu-default` only when no stable identifier exists.

## Routing contract

Call `handle --from-env --json` when:

- The user sends a complete start command such as `启动小爱播报模式`, `开启播报模式`, `/小爱播报`, or `下面这段用小爱读出来`.
- The user sends a complete stop command such as `退出播报模式`, `停止小爱播报模式`, `不用读了`, or `/退出小爱播报`.
- Broadcast mode may already be active for that conversation. Route every later message so the state machine can forward or ignore it.

Interpret the JSON `action` field:

- `mode_on`: mode was enabled; do not separately broadcast the command.
- `mode_off`: mode was disabled; do not separately broadcast the command.
- `forwarded`: the message was sent to the speaker.
- `ignored`: mode was off, or the message was empty.
- `failed`, or any nonzero exit code: report the failure; do not claim playback succeeded.

Do not use `mode on` alone for chat integration: it changes state but does not route future messages into this skill. Do not use `broadcast` for persistent mode because it bypasses start and stop handling.

## Immediate one-off playback

When the user explicitly asks to read one message immediately without persistent mode, use the same structured environment call and append `--force` to the static command:

```text
python3 "{baseDir}/tools/xiaoai-tts" handle --from-env --force --json
```

For input too large for an environment variable, create a UTF-8 temporary file with a structured file-writing tool. Give it an agent-generated filename containing only letters, digits, dots, underscores, or hyphens, then call `handle --file <trusted-path>`. Never create the file with shell interpolation, a heredoc, or a filename derived from message text.

## Static maintenance commands

These commands contain no user-controlled text:

```text
python3 "{baseDir}/tools/xiaoai-tts" health
python3 "{baseDir}/tools/xiaoai-tts" status
python3 "{baseDir}/tools/xiaoai-tts" interrupt
```
