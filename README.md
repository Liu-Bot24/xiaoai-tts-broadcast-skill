# XiaoAI TTS Broadcast Skill

XiaoAI TTS Broadcast Skill 是一个给 OpenClaw 使用的小爱音箱播报 Skill。它通过 [Open-XiaoAI Bridge](https://github.com/coderzc/open-xiaoai-bridge) 的 HTTP API，把 OpenClaw Agent 收到的文字、通知、文章或长篇故事发送到小爱音箱朗读。

这个项目不是独立的小爱音箱服务，也不能替代 Open-XiaoAI Bridge。它的定位是一个配套 Skill：OpenClaw 负责理解你的聊天指令，Open-XiaoAI Bridge 负责连接小爱音箱，本 Skill 负责把文本交给桥接服务播报。

## 能做什么

- 让 OpenClaw Agent 调用小爱音箱播报文字。
- 支持长文本播报模式，适合小说、文章、飞书消息和提前生成好的文本。
- 自动把长文本切成较小段落，按顺序播放，避免一次性 TTS 文本过长导致失败。
- 内置本地状态机，支持“启动播报模式 / 后续消息自动播报 / 退出播报模式”的硬状态。
- 保留原有小爱控制能力，包括健康检查、播放状态、唤醒、文字播报、音频文件、远程 URL 和可选豆包 TTS。
- 支持在 OpenClaw 对话里进入“小爱播报模式”：用户发送正文后，Agent 原样交给小爱读出来。

## 工作方式

你需要先准备好：

- 已部署并连接小爱音箱的 Open-XiaoAI Bridge。
- 能加载本 Skill 的 OpenClaw Agent 运行环境。
- OpenClaw 所在机器能访问 Open-XiaoAI Bridge 的 HTTP API。

典型链路：

```text
飞书或 OpenClaw 对话 -> OpenClaw Agent -> 本 Skill -> Open-XiaoAI Bridge -> 小爱音箱
```

飞书和小爱音箱不是同一个频道。本 Skill 的作用是让 OpenClaw Agent 在收到飞书消息时调用 `xiaoai-tts handle`，由这个命令在本地记录播报模式状态，并在状态开启时把消息转发给 Open-XiaoAI Bridge 播报。

## 安装

下载本仓库或 Release 压缩包，把 `xiaoai-tts` 目录复制到 OpenClaw 使用的 skills 目录中。

安装后的目录结构应类似：

```text
<openclaw-skills-dir>/xiaoai-tts/SKILL.md
<openclaw-skills-dir>/xiaoai-tts/tools/xiaoai-tts
<openclaw-skills-dir>/xiaoai-tts/scripts/...
```

如果解压工具没有保留可执行权限，执行：

```bash
chmod +x <openclaw-skills-dir>/xiaoai-tts/tools/xiaoai-tts
chmod +x <openclaw-skills-dir>/xiaoai-tts/scripts/broadcast_text.py
chmod +x <openclaw-skills-dir>/xiaoai-tts/scripts/broadcast_mode.py
```

在 OpenClaw 的运行环境中配置桥接服务地址：

```bash
export OPENXIAOAI_BASE_URL="http://YOUR_BRIDGE_HOST:9092"
```

然后按你的 OpenClaw 部署方式重新加载 Skill 或重启 OpenClaw。

## 配置项

| 配置项 | 作用 | 是否必需 | 示例 |
| --- | --- | --- | --- |
| `OPENXIAOAI_BASE_URL` | Open-XiaoAI Bridge HTTP API 地址 | 是 | `http://192.168.6.237:9092` |
| `XIAOAI_TTS_STATE_PATH` | 播报模式状态文件路径 | 否 | `~/.xiaoai-tts/broadcast_state.json` |
| `--scope` | 播报状态作用域，用来隔离不同飞书聊天或用户 | 否 | `feishu-default` |
| `--max-chars` | 每段播报的最大字数 | 否 | `450` |
| `--timeout` | 每段播报的超时时间，单位毫秒 | 否 | `600000` |
| `--pause` | 分段之间的停顿秒数 | 否 | `0.4` |

## 使用

检查桥接服务是否可用：

```bash
xiaoai-tts health
```

播报短文本：

```bash
xiaoai-tts text "这是一条小爱播报测试。"
```

播报长文本：

```bash
cat story.txt | xiaoai-tts broadcast --stdin
```

从文件播报：

```bash
xiaoai-tts broadcast --file story.txt
```

调整分段长度：

```bash
xiaoai-tts broadcast --file story.txt --max-chars 500 --pause 0.5
```

开启播报模式：

```bash
xiaoai-tts mode on --scope feishu-default
```

处理一条飞书消息：

```bash
xiaoai-tts handle "要播报的正文" --scope feishu-default
```

退出播报模式：

```bash
xiaoai-tts mode off --scope feishu-default
```

## 在 OpenClaw 里使用播报模式

安装 Skill 后，可以在飞书或 OpenClaw 对话里对 Agent 说：

```text
启动小爱播报模式。
```

之后发送你想朗读的正文。Skill 说明会要求 Agent 不总结、不改写、不续写，而是把正文原样交给 `xiaoai-tts broadcast` 播报。

退出播报模式时说：

```text
退出播报模式。
```

为了让状态足够稳定，建议让 OpenClaw Agent 对相关飞书消息统一调用：

```bash
xiaoai-tts handle "<飞书消息原文>" --scope "<稳定的飞书会话标识>"
```

`handle` 会自行判断：

- 收到启动指令时开启播报模式，不播报指令本身。
- 收到退出指令时关闭播报模式，不播报指令本身。
- 模式开启时，把正文分段转发给小爱音箱播报。
- 模式关闭时，忽略普通正文。

如果拿不到飞书 chat id、open id 或 OpenClaw session id，可以使用固定 scope，例如 `feishu-default`。如果你有多个群聊或多个用户同时使用，建议为每个会话使用不同 scope，避免互相影响。

## 适合的场景

- 先在飞书或其他工具里生成小说，再让小爱音箱朗读。
- 把长文章、通知、会议摘要或待办清单发给 OpenClaw，由小爱播报。
- 让 Agent 在需要播报时调用小爱音箱，而不是把所有内容塞进一次语音对话。

## 边界

本 Skill 只提供 OpenClaw 可调用的工具和本地状态机，不修改 OpenClaw、Open-XiaoAI Bridge 或小爱音箱固件。OpenClaw 仍然需要把飞书消息路由给 Agent，并允许 Agent 调用本 Skill。只要 Agent 对消息调用 `xiaoai-tts handle`，播报模式状态就由工具本身维护，不依赖模型记忆。

## 授权与来源

本项目使用 MIT License。

本 Skill 基于 [coderzc/open-xiaoai-bridge](https://github.com/coderzc/open-xiaoai-bridge) 项目中的 `xiaoai-tts` Skill 修改而来，原项目同样使用 MIT License。原始版权声明保留在 `LICENSE` 中，来源说明见 `NOTICE`。

## 免责声明

本项目是非官方集成项目，与小米、OpenClaw、Open-XiaoAI Bridge 及相关服务提供方不存在隶属、合作、授权、认可或背书关系。请只在你拥有或已获授权控制的设备、账号、服务和网络环境中使用。
