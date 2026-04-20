# XiaoAI TTS Broadcast Skill

This package contains the `xiaoai-tts` skill with long-text broadcast support.

## Install On The OpenClaw Machine

1. Copy `xiaoai-tts-broadcast-skill.zip` to the machine that runs OpenClaw.
2. Unzip it into the OpenClaw skills directory so the final layout is:

   ```text
   <openclaw-skills-dir>/xiaoai-tts/SKILL.md
   <openclaw-skills-dir>/xiaoai-tts/tools/xiaoai-tts
   <openclaw-skills-dir>/xiaoai-tts/scripts/...
   ```

3. Make the tool executable if your unzip tool does not preserve permissions:

   ```bash
   chmod +x <openclaw-skills-dir>/xiaoai-tts/tools/xiaoai-tts
   chmod +x <openclaw-skills-dir>/xiaoai-tts/scripts/broadcast_text.py
   chmod +x <openclaw-skills-dir>/xiaoai-tts/scripts/broadcast_mode.py
   ```

4. Set the Open-XiaoAI Bridge URL in the environment where OpenClaw runs:

   ```bash
   export OPENXIAOAI_BASE_URL="http://YOUR_BRIDGE_HOST:9092"
   ```

   Optional: set a custom state file for broadcast mode:

   ```bash
   export XIAOAI_TTS_STATE_PATH="$HOME/.xiaoai-tts/broadcast_state.json"
   ```

5. Reload or restart OpenClaw according to that machine's normal skill-loading workflow.

## Test

From the OpenClaw machine:

```bash
xiaoai-tts health
echo "这是一段小爱播报测试。" | xiaoai-tts broadcast --stdin
xiaoai-tts handle "启动小爱播报模式" --scope feishu-default --dry-run
xiaoai-tts handle "这是一段飞书正文。" --scope feishu-default --dry-run
xiaoai-tts handle "退出播报模式" --scope feishu-default --dry-run
```

## Usage In OpenClaw

Ask the agent to enter XiaoAI broadcast mode. After that, send the text you want read aloud. The skill instructions tell the agent to pass the text through unchanged and call:

```bash
xiaoai-tts handle --stdin --scope <stable-feishu-scope>
```

Send "退出播报模式" or "停止播报模式" to leave the mode.
