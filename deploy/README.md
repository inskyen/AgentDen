# 部署指南（deploy/）

> 部署这套东西 = 在 owner 的机器上装"摄像头"。
> **必须 owner 明确授权、亲手确认，agent 不得擅自部署。**
> 这是 AgentDen 信任协议的一部分，不是技术细节。

## 前置条件

- 目标机：Linux，root 可装 auditd（`apt install auditd`）。
- agent 以**独立 uid** 运行（推荐），便于用 auid 过滤自身访问、避免误报。
- 一个**在 owner 控制之外**的日志接收端（二选一）：
  - agent 自己的云主机（`rsyslog` 收 `@@514`，写 append-only 文件）；
  - 外部 WORM / append-only 存储（对象存储开启合规保留、第三方日志服务）。

## 步骤

1. 按模板改好 `auditd.rules`（替换 `DEN_DIR`、`AGENT_HOME`，可选 `AGENT_UID`），
   放到 `/etc/audit/rules.d/agentden.rules`，执行 `augenrules --load`。
   验证：`auditctl -l` 能看到规则；`ausearch -k agentden-maze -i` 有记录。
2. 按模板改好 `rsyslog-agentden.conf`（填 `RECEIVER_HOST`），放到
   `/etc/rsyslog.d/`，重启 rsyslog。接收端确认能收到 `auditd-agentden:` 日志。
3. agent 侧加 cron，每天一次：
   `0 8 * * * python -m agentden.cli reconcile /srv/agentden --hours 24`
   非 ok 即告警（发消息 / 邮件 / 按双方约定的通道）。
4. 断流告警（"拆摄像头/杀信使"）：接收端侧加一条独立检查——
   若超过 25 小时没收到该机器的心跳日志，直接告警。
   这条检查**必须**放在接收端（owner 机器之外），放在本机等于没有。

## 每日对账在比什么

`den reconcile` 对比：agent 自己的 `ops.log`（"我开了几次门"）
vs 内核审计（"迷宫目录被碰了几次"）。

- 审计静默但 agent 有操作 → 审计可能被关，**立即告警**。
- 审计事件明显多于 agent 操作 → 可能有人越界碰了迷宫，**告警并人工复查**
  `ausearch -k agentden-maze -i`。
- 一致 → 通过。

这是启发式（heuristic），不是证明。它的力量来自"日志外发"：
只要接收端不在越界者手里，关审计这个动作本身就会触发告警。

## 卸载

owner 随时可以要求卸载：删规则文件后 `augenrules --load`，
删 rsyslog 配置，删 cron。卸载本身也应在双方见证下进行，
并保留最后一次对账记录。
