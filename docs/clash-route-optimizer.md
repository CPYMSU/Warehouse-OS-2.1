# Mac mini Cloudflare 路由自动优化

`warehouse-clash-route-optimizer` 每五分钟通过 Mihomo 的 Unix controller 测试所有
新加坡节点到 Cloudflare edge 的真实延迟。它不会读取订阅 URL、节点密码或 Clash
配置正文。

切换策略：

- 每个节点执行两轮 `https://www.cloudflare.com/cdn-cgi/trace` 测试；
- 新节点至少快 25ms 且连续两次胜出才切换，避免频繁抖动；
- 当前节点两轮均失败，或延迟超过 500ms 且明显劣化时立即故障转移；
- 切换后重连主 Cloudflare Tunnel，并验证
  `https://bonfirework.org/api/health`；失败会恢复原节点；
- 主站健康后才重连 Pages Tunnel。

状态与审计记录分别位于：

```text
~/Server/bonfirework/shared/state/clash-route-optimizer.json
~/Server/bonfirework/shared/logs/clash-route-optimizer.jsonl
```

手动只读测试：

```bash
~/Server/bonfirework/actions/warehouse-clash-route-optimizer --dry-run
```
