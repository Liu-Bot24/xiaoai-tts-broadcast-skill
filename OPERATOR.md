# OpenClaw Operator Guide

This guide defines the safe routing contract between OpenClaw chat messages and this skill.

## Required routing

For every message in a conversation whose XiaoAI broadcast mode may be active, call the exec tool with a fixed command and structured environment values:

```json
{
  "command": "python3 \"{baseDir}/tools/xiaoai-tts\" handle --from-env --json",
  "env": {
    "XIAOAI_TTS_MESSAGE": "<exact current message>",
    "XIAOAI_TTS_SCOPE": "<stable conversation id>"
  }
}
```

Use `python` instead of `python3`, or `py -3` on Windows, when that is the available interpreter. Keep the rest of the command unchanged.

Never concatenate or interpolate message text or the conversation ID into the command string. Quoting user text is not an adequate boundary because the exec tool starts a shell. Do not invoke a `.cmd` file with untrusted arguments; Windows parses its command line through `cmd.exe` before the batch body runs.

Use one stable scope for the start command, body messages, and stop command. Prefer the channel chat ID, sender ID, or OpenClaw session ID. Fall back to `feishu-default` only when no stable ID exists.

## State transitions

Examples of complete start commands:

```text
启动小爱播报模式
开启播报模式
/小爱播报
下面这段用小爱读出来
```

Examples of complete stop commands:

```text
退出播报模式
停止小爱播报模式
不用读了
/退出小爱播报
```

Commands match the complete normalized message. A sentence that merely mentions one of these phrases is ordinary content.

The JSON `action` is one of `mode_on`, `mode_off`, `forwarded`, `ignored`, or `failed`. Treat a nonzero process exit code as failure even if stdout contains data.

Do not call only `mode on`; that changes state but does not route future chat messages into this skill. Do not use `broadcast` for stateful chat mode because it bypasses command handling.

## Long messages

For text too large for an environment variable, write the exact text using a structured file tool to a UTF-8 temporary file whose agent-generated name contains only letters, digits, dots, underscores, or hyphens. Then call:

```text
python3 "{baseDir}/tools/xiaoai-tts" handle --file "<trusted-generated-path>" --json
```

Pass the stable scope through `XIAOAI_TTS_SCOPE`. Never use shell redirection, a heredoc, or a filename derived from the message.

## Verification

The following PowerShell commands exercise the input boundary without changing state:

```powershell
$env:XIAOAI_TTS_MESSAGE = '他说“不用读了”只是台词'
$env:XIAOAI_TTS_SCOPE = 'verification-chat'
python .\tools\xiaoai-tts handle --from-env --dry-run --json
```

`--dry-run` must not create or modify a state file or lock file. For a real Bridge check, run `python .\tools\xiaoai-tts health` and require exit code zero.
