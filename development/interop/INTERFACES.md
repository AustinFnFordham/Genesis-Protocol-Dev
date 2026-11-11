# Provider-independent boundary

The implemented public client reads the same public ledger, exporter, page budgets
and revision fingerprint from separate processes. It never opens hidden/. Client
names are labels, not proof of Claude, ChatGPT or Gemini compatibility.

A proposed adjudication interface accepts campaign_id, action_id, expected_revision,
expected_ledger_head, contract_version, declaration and a scoped identity.
Private GM context is obtained by a separately authorized worker. Public clients
cannot supply their own GM context, accept their own repair ruling, or write ledger
events directly.

An authorized commit adapter validates domain rules and field ownership, then uses
the existing ledger batch interface with the current worker lease and an immutable
idempotency key. A conflicting revision rejects the proposal. Accepted batch recovery
resumes the exact accepted bytes and never requests new dice. Publication retains
pages-first and snapshot-last ordering after git durability checks.

This increment implements public refresh and the existing local batch adapter.
Remote authentication, provider adjudication adapters and end-to-end provider
interchangeability are not implemented or certified.
