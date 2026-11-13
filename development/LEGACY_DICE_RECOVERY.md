# Canonical legacy dice recovery

The canonical reconciliation is on `rc/canonical-dice-recovery-f241ea6`, based
on `f241ea6`. It selects B's single versioned resolver, adds A's audit and batch
barriers and unique tests, and requires explicit recovery for interrupted
unkeyed commands. Release remains **HOLD**.

See [DICE_RECOVERY_RECONCILIATION.md](DICE_RECOVERY_RECONCILIATION.md) for the
code-level comparison, exact retry contract, preserved coverage, confirmed
verification, persisted-format boundary, and remaining staging blockers.
