# XiaoAI TTS Broadcast Skill

XiaoAI TTS Broadcast Skill 是一个 OpenClaw Skill，用来把飞书、聊天消息、文章、通知或小说文本转发给小爱音箱朗读。它不直接连接小爱音箱，而是调用 [Open-XiaoAI Bridge](https://github.com/coderzc/open-xiaoai-bridge) 的 HTTP API，由桥接服务控制小爱音箱播放。

它解决的问题很简单：你可以先在飞书或 OpenClaw 里准备好一段文本，再让小爱音箱读出来；也可以开启播报模式，让同一个聊天会话里的后续消息自动转成小爱播报，直到你发送退出指令。

## 功能

- 通过 Open-XiaoAI Bridge 调用小爱音箱原生 TTS。
- 支持长文本自动分段，适合小说、长文、会议摘要和通知。
- 支持有状态播报模式：启动后，同一会话里的后续消息会继续转发给小爱，退出后停止。
- 支持 Linux、macOS、Windows、WSL 和常见 OpenClaw 容器环境。
- 保留健康检查、播放状态、唤醒、打断、文本播报、音频文件和 URL 播放能力。

## 工作链路

```text
飞书或聊天消息 -> OpenClaw Agent -> 本 Skill -> Open-XiaoAI Bridge -> 小爱音箱
```

飞书和小爱音箱不是同一个频道。这个 Skill 的作用是让 OpenClaw Agent 在收到消息时调用 `xiaoai-tts handle`，由工具自己保存播报模式状态，并在状态开启时把消息交给小爱朗读。

## 安装

如果 OpenClaw 支持从 GitHub 链接安装 Skill，直接安装这个仓库：

```text
https://github.com/Liu-Bot24/xiaoai-tts-broadcast-skill
```

如果手动安装，把仓库解压或克隆到 OpenClaw 的 skills 目录。技能根目录需要包含：

```text
SKILL.md
tools/xiaoai-tts
tools/xiaoai-tts.cmd
xiaoai-tts/scripts/...
```

也可以只复制仓库里的 `xiaoai-tts` 子目录作为 Skill；这种方式下技能根目录应包含：

```text
SKILL.md
tools/xiaoai-tts
tools/xiaoai-tts.cmd
scripts/...
```

Linux/macOS 如果工具没有执行权限，运行：

```bash
chmod +x <skill-dir>/tools/xiaoai-tts
```

Windows 原生环境使用 `tools\xiaoai-tts.cmd`，并安装 Python 3.8 或更新版本。

## 配置

在 OpenClaw 实际运行的环境里设置桥接服务地址：

```bash
OPENXIAOAI_BASE_URL="http://192.168.6.237:9092"
```

如果 OpenClaw 由 systemd、Docker、Windows 服务或守护进程启动，要把这个变量写进对应的持久环境配置里，而不是只在临时终端里 `export`。

| 配置项 | 作用 | 推荐值 |
| --- | --- | --- |
| `OPENXIAOAI_BASE_URL` | Open-XiaoAI Bridge HTTP API 地址 | `http://192.168.6.237:9092` |
| `XIAOAI_TTS_STATE_PATH` | 播报模式状态保存位置 | 默认即可 |
| `--scope` | 区分不同飞书聊天、用户或会话 | 飞书 chat id / open id / session id |
| `--max-chars` | 每段最大字数 | `450` |
| `--timeout` | 每段播放超时，毫秒 | `600000` |
| `--pause` | 分段间隔，秒 | `0.4` |

## 验证

在 OpenClaw 运行环境里执行：

```bash
xiaoai-tts health
xiaoai-tts text "这是一条小爱播报测试。" --blocking
```

Windows PowerShell：

```powershell
.\tools\xiaoai-tts.cmd health
.\tools\xiaoai-tts.cmd text "这是一条小爱播报测试。" --blocking
```

如果提示找不到 `xiaoai-tts`，把 `<skill-dir>/tools` 加入 OpenClaw 运行环境的 `PATH`，或让 Agent 使用完整路径调用工具。

## 使用

直接播报短文本：

```bash
xiaoai-tts text "这是一条小爱播报测试。" --blocking
```

播报长文本：

```bash
xiaoai-tts broadcast --file story.txt
cat story.txt | xiaoai-tts broadcast --stdin
```

开启播报模式：

```bash
xiaoai-tts handle "启动小爱播报模式" --scope feishu-default
```

处理后续消息：

```bash
xiaoai-tts handle "这里是要朗读的正文。" --scope feishu-default
```

退出播报模式：

```bash
xiaoai-tts handle "退出播报模式" --scope feishu-default
```

`handle` 会自动判断启动、退出、转发或忽略。启动和退出指令本身不会被播报。

## 给 OpenClaw Agent 的安装提示

可以把这段发给另一台设备上的 OpenClaw：

```text
请安装这个 OpenClaw Skill：https://github.com/Liu-Bot24/xiaoai-tts-broadcast-skill
安装后把 OPENXIAOAI_BASE_URL 持久配置为 http://192.168.6.237:9092，并确认 xiaoai-tts health 可以运行。
飞书播报模式请按仓库里的 OPERATOR.md 接入。
```

## 授权与来源

本项目使用 MIT License。

本 Skill 基于 [coderzc/open-xiaoai-bridge](https://github.com/coderzc/open-xiaoai-bridge) 项目中的 `xiaoai-tts` Skill 修改而来，原项目同样使用 MIT License。原始版权声明保留在 `LICENSE` 中，来源说明见 `NOTICE`。

## 免责声明

本项目是非官方集成项目，与小米、OpenClaw、Open-XiaoAI Bridge 及相关服务提供方不存在隶属、合作、授权、认可或背书关系。请只在你拥有或已获授权控制的设备、账号、服务和网络环境中使用。
