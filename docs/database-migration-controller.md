# Warehouse OS 后台数据库迁移控制器

数据库升级与应用部署是两个独立控制面。API、Runtime Controller、Browser
Runtime 只使用 `warehouse_os` 应用角色；它们的启动命令不得运行 Alembic，也不
能读取 migration DSN。只有短生命周期的后台数据库控制器使用
`warehouse_migrator`。

## 发布顺序

1. 部署电脑完成全部代码、前端、Shell 和测试验证，并并行构建 Mac/Vultr 候选镜像。
2. Vultr 控制器先处理 `schema` revision，使用节点本地
   `app.alembic_version_standby` 游标；它不改写主库复制过来的
   `app.alembic_version`。
3. Vultr schema 状态成功后，Mac 控制器取得 PostgreSQL advisory lock，制作并
   验证 custom-format 备份，然后处理主库 revision。
4. `primary_data` revision 只在 Mac 执行，通过 logical replication 到达 Vultr；
   Vultr 只推进自己的本地 schema 游标。
5. 复制的主库 Alembic 游标追平后，后台自动执行 `REFRESH PUBLICATION`，将
   schema revision 新建的表纳入订阅，并等待全部 relation 回到 ready。
6. 两端候选随后才进入 `prepared`。正式
   `activate` 只切换系统镜像与流量，60 秒窗口内不执行数据库操作。

迁移任务状态位于节点受限目录 `shared/database-migrations/<release>/`：

- `request.json`：不可变 release、Git SHA、目标 revision、节点角色；
- `status.json`：`planning → backing_up → migrating → verifying → succeeded`；
- 失败状态只包含脱敏错误、稳定错误码和允许的恢复动作，不记录密码或 DSN。

重复提交同一 release 是幂等的。每个数据库还使用固定 advisory lock，避免两个
worker 同时迁移。

## Migration 编写契约

`20260805_0078` 是 legacy baseline。它之后的每个 revision 必须声明：

```python
warehouse_scope = "schema"
```

或：

```python
warehouse_scope = "primary_data"
```

- `schema` 可以执行 CREATE/ALTER/DROP/GRANT 等结构操作，禁止
  INSERT/UPDATE/DELETE/COPY。
- `primary_data` 可以修改应用数据，禁止结构操作。
- 同一 revision 混合 DDL 与 DML、动态拼接 SQL、未声明 scope，都会在迁移前
  fail closed。
- 需要“新增字段并回填”时必须拆成 schema revision 与后续 primary_data
  revision；最终删除旧字段必须等所有线上代码不再读取它后，以新的 schema
  revision 完成。

策略文件为 `backend/alembic/migration-policy.json`。发布镜像中的策略、migration
源码和目标 head 都包含在不可变 manifest 中。

## 备用库自动恢复

如果 Vultr 落后于 legacy baseline 或其本地 schema 无法安全前进，控制器返回
`reseed_standby_control_database`。受信任的当前 release 随后执行一次自动恢复：

1. 验证节点确为 standby，且应用/migrator 两个角色均被只读 fence；
2. 对现有 Vultr 控制库制作校验备份；
3. 从 Mac publication 读取 schema，重建且仅重建 Vultr `warehouse_os` 控制库；
4. 以 `copy_data=true` 重建 subscription；
5. 等待全部 publication tables 为 ready，并核对 Alembic 与关键表笔数；
6. 再次确认只读 fence，恢复 Vultr API 候选。

自动恢复不会删除 Mac 主库，也不会触碰 HDD 上的用户托管数据库。每个 release
最多自动 reseed 一次；第二次失败会停止发布并保留备份与状态证据。

## 运维命令

```bash
ops/deploy migration-start RELEASE
ops/deploy migration-status RELEASE
ops/deploy migration-wait RELEASE
ops/deploy migration-reconcile RELEASE
```

日常仍使用 `ops/cluster/rolling-deploy smart`。上述命令供编排器和故障审计使用，
不需要人工执行 SQL。
