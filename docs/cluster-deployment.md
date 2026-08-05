# Warehouse OS 双节点智能发布

生产发布由部署电脑统一编排，服务器不再各自决定发布顺序。唯一入口是：

```bash
ops/cluster/rolling-deploy smart
```

发布分成两个阶段：

1. `prepare`：部署电脑先验证干净 Git tree、前端产物、Shell 合约和完整测试；随后并行向 Mac primary 与 Vultr standby 上传不可变 release。两端在此阶段完成校验、备份、镜像构建、迁移和候选健康检查，但不切换流量。
2. `activate`：只有两端的 `prepared-status` 都通过，部署电脑才同时发出激活命令。Mac 更新 primary，Vultr 原子切换 blue/green upstream。激活窗口默认不得超过 60 秒。

数据库仍遵循严格单写：只有 Mac primary 的 prepare 可以执行迁移。Vultr standby 不执行 DDL，而是等待复制数据库达到 release 声明的 Alembic head，再通过只读候选验证。Browser worker 和 Runtime Controller 不在 standby 启动。

若一端激活失败，编排器会回滚已经成功激活的另一端。激活成功后还会从两端各自的受限管理通道读取 readiness，要求节点身份、Git SHA 和数据库 head 一致；不能用公网域名冒充 standby 健康检查。

可配置项：

- `WAREHOUSE_CLUSTER_PREFLIGHT=full|basic`：默认 `full`，生产不得降低。
- `WAREHOUSE_CLUSTER_ACTIVATION_SLO_SECONDS`：默认 `60`。
- `WAREHOUSE_PRIMARY_*`、`WAREHOUSE_STANDBY_*`：覆盖节点地址、用户、密钥、manager 和 incoming 路径。

服务器上的传统 `install RELEASE MODE` 仍保留兼容性，内部等价于连续执行 `prepare` 和 `activate`。日常生产发布应始终使用集群入口。

Mac 的受限 SSH forced-command gate 与 manager 同属 release 控制面；每次成功激活会同时更新两者，避免 manager 已支持新协议但实际授权入口仍停留在旧版本。
