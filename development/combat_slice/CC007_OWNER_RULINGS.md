# CC-007 owner rulings amendment — v1 (recorded 2026-11-25)

**What this amends:** `COMBAT_RULES_AUDIT_2026-11-24.md` §7. That audit was based on `6bf7aa8`.

**What it records:** the owner's rulings on audit decisions D-2, D-3, D-11 and D-12.

**Authority:** these rulings apply only to the combat sandbox (`cc-sandbox-*` rulesets). Nothing here changes live campaign rules (`TURN_CONTRACT.md`, Hask Meadow, `shared-0002`) unless a separate live adoption is recorded.

## 1. Which kind of ruling each one is

| Ruling | Kind | Scope |
|---|---|---|
| Minor Telekinesis grant (Jedi Fundamentals, 2026-11-11) | **Existing campaign ruling.** `approved_provisional`, unchanged by this amendment. | `starwars_litrpg` |
| Taunt: ties go to the target (2026-11-17, `tb4_taunt`) | **Existing campaign ruling**, unchanged | `starwars_litrpg` |
| Narrative Consequences d6 (2026-11-15) | **Existing live adoption** for `hask_meadow_r2`. It is not modified here; only its boundary (R-1) is restated. | `hask_meadow_r2` |
| R-1 to R-4 below | **New approvals, sandbox only** | combat sandbox |

## 2. Rulings

### R-1 · The d20 decides objective outcomes (D-11, D-12)

1. The **d20 decides objective outcomes**: attacks, checks, saves, contests and critical hits.
2. **Narrative Consequences** add complications and opportunities **beside** that outcome. They can never turn a success into a failure, or a failure into a success.
3. A **natural 20** keeps its mechanically valid critical result: the damage dice are doubled (sandbox rule). Parry cannot turn a critical hit into a miss.
4. **Opposed contests: the defender wins ties.** This applies to every contest in the sandbox. The Taunt ruling is one case of it.
5. Any additional consequence must be **validated separately** (Atomic) before it affects the world.

### R-2 · A dropped lightsaber deactivates (D-2)

- A dropped lightsaber deactivates.
- Retrieving it by hand (`recover_weapon`) or by Telekinesis (`minor_telekinesis`) returns it **unlit**.
- Igniting it costs its normal **Object interaction** (`toggle_blade`).

### R-3 · Feint expiry (D-3)

- Feint advantage **expires at the end of the feinter's turn** if it hasn't been used.
- **Status:** the carry-over bug (audit X-1) is fixed in CC-007 A, with a dedicated regression test.

### R-4 · Implementing missing source-backed basics (CC-007 brief §2)

**Approved to implement as written on the sheet:**
- Grapple: size limit, escape contest, drag at half speed, release conditions, correct action cost.
- Sentinel Balance: 2 uses per long rest.

**Battle Insight's duration and concentration:** to be addressed only as far as the engine's timing and concentration support allows. Anything missing is documented, not invented.

## 3. Still open (not ruled here)

| Audit item | Topic |
|---|---|
| D-1 | Telekinesis repositioning consequence |
| D-4 to D-8 | Dice modes |
| D-9 | SA-001 adoption (a study follows in CC-007) |
| D-10 | Sandbox defaults |
| D-13 | Battle Insight concentration model |
| D-16 | Telekinesis open items |
| D-17 | Undefined Crucible elements |

**Crucible direction recorded:** simulate both d8 baseline + d4 modifiers (preferred) and d4 routine + d8 escalation. This is a separate design track and is not part of CC-007.
