# Warehouse OS 双节点智能发布

生产发布由 Mac mini production runner 统一编排，服务器不再各自决定发布顺序。
任何已获 GitHub 权限的电脑终端都使用同一个入口：

```bash
ops/fast-deploy smart
```

该命令只向 GitHub 提交调度请求；真正的构建、服务器密钥、双机连接和数据库门禁
全部留在 Mac mini。Mac 本机紧急运维可使用 `ops/fast-deploy local smart`，底层
唯一编排器仍是 `ops/cluster/rolling-deploy`。

发布分成三个互相隔离的阶段：

1. `prepare`：部署电脑先验证干净 Git tree、前端产物、Shell 合约和完整测试；随后并行向 Mac primary 与 Vultr standby 上传不可变 release、构建镜像，不改数据库、不切换流量。
2. `database gate`：后台数据库控制器先完成 Vultr schema，再完成 Mac 主库备份与迁移，最后等待复制游标追平。部署进程只提交和读取持久任务状态，不持有 migration DSN。
3. `activate`：只有两端的 `prepared-status` 都通过，部署电脑才同时发出激活命令。Mac 更新 primary，Vultr 原子切换 blue/green upstream。激活窗口默认不得超过 60 秒，窗口内不执行备份或 migration。

数据库仍遵循严格单写。Vultr 只先执行静态验证通过的 schema revision，并使用节点本地 Alembic 游标；数据回填只在 Mac 执行并经 logical replication 到达 Vultr。API、Browser worker 和 Runtime Controller 都拿不到 migration 身份。Browser worker 和 Runtime Controller 不在 standby 启动。完整契约见 `docs/database-migration-controller.md`。

若一端激活失败，编排器会回滚已经成功激活的另一端。激活成功后还会从两端各自的受限管理通道读取 readiness，要求节点身份、Git SHA 和数据库 head 一致；不能用公网域名冒充 standby 健康检查。

可配置项：

- `WAREHOUSE_CLUSTER_PREFLIGHT=full|basic`：默认 `full`；PR 前完成 full，已验证的
  main release 在正式切换时使用 `basic`，避免重复测试拖慢发布。
- `WAREHOUSE_CLUSTER_ACTIVATION_SLO_SECONDS`：默认 `60`。
- `WAREHOUSE_PRIMARY_*`、`WAREHOUSE_STANDBY_*`：覆盖节点地址、用户、密钥、manager 和 incoming 路径。

服务器上的传统 `install RELEASE MODE` 仅保留兼容性。日常生产发布应始终使用
`ops/fast-deploy`，不要让不同终端自行发明部署顺序。

Mac 的受限 SSH forced-command gate 与 manager 同属 release 控制面；每次成功激活会同时更新两者，避免 manager 已支持新协议但实际授权入口仍停留在旧版本。
