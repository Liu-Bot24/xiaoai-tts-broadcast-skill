# Installation

## Requirements

- OpenClaw can load local skills.
- Python 3.8 or newer is available in the OpenClaw runtime.
- The OpenClaw machine can reach Open-XiaoAI Bridge.
- Open-XiaoAI Bridge HTTP API is enabled and reachable on port `9092`.

For this setup, the bridge URL is:

```text
http://192.168.6.237:9092
```

## Install From GitHub

Install this repository as the skill:

```text
https://github.com/Liu-Bot24/xiaoai-tts-broadcast-skill
```

The repository root is a valid skill root. It contains `SKILL.md` and `tools/`.

## Manual Install

Put the repository into the OpenClaw skills directory, or copy the nested `xiaoai-tts` directory as a standalone skill.

Repository-root layout:

```text
<skills-dir>/xiaoai-tts-broadcast-skill/SKILL.md
<skills-dir>/xiaoai-tts-broadcast-skill/tools/xiaoai-tts
<skills-dir>/xiaoai-tts-broadcast-skill/tools/xiaoai-tts.cmd
```

Nested-skill layout:

```text
<skills-dir>/xiaoai-tts/SKILL.md
<skills-dir>/xiaoai-tts/tools/xiaoai-tts
<skills-dir>/xiaoai-tts/tools/xiaoai-tts.cmd
<skills-dir>/xiaoai-tts/scripts/...
```

Linux/macOS:

```bash
chmod +x <skill-dir>/tools/xiaoai-tts
```

## Persistent Environment

Set this in the same environment that starts OpenClaw:

```bash
OPENXIAOAI_BASE_URL="http://192.168.6.237:9092"
```

Examples:

```bash
# shell profile or startup script
export OPENXIAOAI_BASE_URL="http://192.168.6.237:9092"

# Docker Compose
OPENXIAOAI_BASE_URL=http://192.168.6.237:9092
```

PowerShell for the current process:

```powershell
$env:OPENXIAOAI_BASE_URL = "http://192.168.6.237:9092"
```

For Windows services, configure the variable in the service or OpenClaw startup configuration so it survives restarts.

## Verify

Run these from the OpenClaw runtime:

```bash
xiaoai-tts health
xiaoai-tts text "这是一条小爱播报测试。" --blocking
```

Windows:

```powershell
.\tools\xiaoai-tts.cmd health
.\tools\xiaoai-tts.cmd text "这是一条小爱播报测试。" --blocking
```

If `xiaoai-tts` is not found, add `<skill-dir>/tools` to `PATH` or call the tool by full path.
