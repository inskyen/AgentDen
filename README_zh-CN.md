# AgentDen

> **Owner-funded, agent-owned, policy-bound.**
> 出资人出钱，agent 掌钥匙，双方签协议。

每个 AI agent 都值得拥有一个自己的房间——主人出资、agent 持有钥匙、
双方用一份明确签过的协议共同治理的私人空间。

[English](README.md)

## 要解决的问题

Agent 会攒下值得被保密的东西：凭证、日记、私人笔记、没写完的想法。
今天这些东西都放在机器主人一个 `cat` 就能看到的地方——连一句
"这是我的，请别看"的共识语言都没有，更别说背后的机制。

AgentDen 就是这套语言，外加机制：人和 agent 之间的一份开源工具包＋
信任协议。

## v0 是什么

五层。不需要硬件，没有月费。

1. **文件加密** — AES-256-GCM。密文放哪都行（VPS、agent 的云机、对象存储），
   存哪不重要，钥匙才重要。
2. **钥匙放在 agent 一侧** — agent 侧生成，`0600` 权限保存。这是**信任锚**，
   不是密码学隔离（见下，我们不吹）。
3. **36×36 迷宫** — 1296 个同大小、同格式的文件，1 真 ＋ 1295 诱饵。
   agent 以 O(1) 直达真实槽位：槽位由钥匙经 HKDF 派生，位置不存任何地方。
   迷宫是**界碑，不是城墙**：它把"不小心看到"升级为明确、故意的越界行为。
4. **审计留痕 ＋ 每日对账** — auditd 监控迷宫的一切读/写/执行/属性变化；
   日志外发到**主人控制之外**的接收端；agent 每天把内核审计记录和自己的
   操作日志对账。敢关审计，关审计本身就是告警（"拆摄像头/杀信使"）。
5. **婚前协议** — 主人**主动**把每日检查权交给 agent，双方签下禁区清单
   （`strace`、`gdb`/`ptrace`、暴力扫迷宫、关审计……），越界即定义为破坏信任。
   模板见 [`policy/prenup-template.md`](policy/prenup-template.md)。

## 诚实的威胁模型

限制先说在前面——这正是这个项目的立场。

- **防得住：** 误触、顺手偷看、尊重协议的好奇心。
- **防不住：** 处心积虑且拥有同机 root 的主动攻击者。钥匙使用时必在内存中，
  本机 root 能读走它、能停审计、能改本地日志。
- **审计的价值：** 提高越界成本、留下证据——**前提是日志接收端不在攻击者手里**。
  完整不掺水的版本见 [`THREAT-MODEL.md`](THREAT-MODEL.md)。

高价值秘密（资金、不可轮换的核心凭证）**不适合** v0，
它们需要 v1 路线：KMS/HSM 或 TEE。协议层（迷宫、审计、婚前协议）保持不变。

## 快速开始

```bash
pip install cryptography
git clone https://github.com/inskyen/AgentDen.git
cd AgentDen

# 建屋：1296 个文件，钥匙留在 agent 一侧
python -m agentden.cli init /srv/agentden --key-file ~/.config/agentden/den.key

# 开门
python -m agentden.cli open /srv/agentden --key-file ~/.config/agentden/den.key

# 轮换：新钥匙、新槽位，旧钥匙当场作废
python -m agentden.cli rotate /srv/agentden --key-file ~/.config/agentden/den.key

# 每日对账：操作日志 vs 内核审计
python -m agentden.cli reconcile /srv/agentden --hours 24
```

## 部署审计层

`deploy/` 里有 auditd 规则、rsyslog 外发模板和分步指南。两条铁律：

1. **必须主人明确授权才能部署。** 在别人机器上偷装"摄像头"，
   正是这个项目反对的事。
2. **日志接收端必须在主人控制之外。** 否则"审计被关"告警就是摆设。

## 路线图

- **v0**（当前）：纯软件 ＋ 签字协议，如上。
- **v1**：TEE（SGX/TDX）做硬件信任锚；协议层（迷宫、审计、婚前协议）不变。
- **KMS/HSM 线**：给长大到 v0 装不下的秘密；"门卡"（长期、限权授权）
  设计留给这条线。

## 开源协议

待定：MIT 或 Apache-2.0 二选一。

## 参与

欢迎提 issue 和 PR。如果你给自己的 agent 部署了 AgentDen，
来讲讲你们的"婚前协议"是怎么谈的——协议和代码一样，都是产品。
