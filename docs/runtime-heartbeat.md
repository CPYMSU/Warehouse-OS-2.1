# Runtime liveness and work progress

The Runtime Controller used to update its heartbeat only after its synchronous
work loop returned. A normal build taking longer than the 30-second provider
expiry could therefore appear offline. The readiness marker also aged during
normal long work.

`RuntimeHeartbeat` now runs alongside, not instead of, that work loop. It uses
one daemon thread, fresh dedicated PostgreSQL connections, a maximum five-second
interval, a three-second connection/statement timeout, a one-second lock timeout,
and TCP keepalive/user-timeout settings. DNS resolution remains subject to the
host resolver. It never claims tasks, renews leases, changes business records,
updates work-success timestamps, or clears a controller error. The original
serial scheduling and 30-second provider expiry remain unchanged.

The work thread records local monotonic progress after each completed phase.
A phase with no return for three hours triggers the independent progress
watchdog: the worker is reported degraded and its readiness marker stops being
refreshed. This conservative bound accommodates the existing two-hour job limit
plus image preparation; it is not a new task timeout or evidence of fine-grained
task progress. Existing task-specific deadlines still apply. Liveness cannot
keep a stalled worker green forever. Work-loop success, not the background
thread, clears degraded status. Existing draining/error state is preserved.

The marker is refreshed only after a committed heartbeat while the owning work
thread is alive and the progress watchdog is not overdue. Database failures are
logged by exception type only. The normal provider expiry still detects loss
of database reachability. Shutdown stops further periodic pulses; a stopped
worker can remain visible for the ordinary expiry interval.

## Verification and release

- Unit coverage: dedicated bounded connections, no forged progress, error/status
  preservation, watchdog behavior, background operation, owner exit, shutdown,
  and redacted failure recovery.
- Disposable PostgreSQL coverage: a real 36-second work wait remains online;
  SQL upsert preserves work timestamps, errors, metadata and draining/degraded
  states; row-lock contention times out and a later pulse recovers.
- No schema migration, permission change, application activation or change to
  worker count. Existing task lease renewal is outside this patch; do not add
  workers on the assumption that a liveness pulse renews task ownership.
- Use the existing coordinated Mac/standby publication route, verify both
  immutable candidates and no-migration plans, check work queues before switching,
  retain the previous images/releases, and verify platform plus hosted application
  routes afterwards. Do not patch live container files.

The deployment-contract test's known workflow list was brought up to date with
the two already-existing digital-asset workflows. No workflow was added or
changed, and the existing lightweight CI assertions remain in force.
