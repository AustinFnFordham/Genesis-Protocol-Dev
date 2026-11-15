# One shared mobile gateway — deployment proposal, not deployed

## What you would approve

One **Render Starter Docker web service in Ohio**, one **1 GB persistent disk**
mounted at `/var/data`, and **Auth0 Free** for owner login and OAuth. One process
serves the same `/mcp` endpoint to ChatGPT and Gemini. There is no model backend:
each conversation does its own GM reasoning. The existing `staging/provider-shared`
Git history remains the sole campaign authority. There is no new campaign database.

Expected base hosting: **$7/month service + $0.25/month disk = $7.25/month** before
tax, bandwidth/build overages or plan changes. Auth0 currently lists Free at $0
for up to 25,000 monthly active users. Use its included tenant domain, not a paid
custom domain. Existing ChatGPT/Gemini plan charges continue; no model API calls
or API keys are needed. These are published plan prices, not a measured hosting
bill. Confirm the checkout price before approving payment. Nothing has been
provisioned, billed, enabled or deployed by this work.

Accounts needed: your existing GitHub repository account; a Render account linked
to GitHub; an Auth0 account/tenant; your existing ChatGPT and personal Google/Gemini
accounts. Mobile custom-app availability must be checked on those actual accounts.

## Why these two implementations were reconciled this way

The compared remote commits are GPT `3e87d45849c5275fd2aa4c9dcd2ae7977315b762`
and Gemini `2a1e324abc81f94e3550851d9d6eb7326c74b0ee`. Both original branches are
preserved. The new branch starts from GPT's commit and selectively ports Gemini's
public digest/compact projection, cursor checks and read-only discovery behavior.

| Area | GPT implementation | Gemini implementation | Reconciled candidate |
| --- | --- | --- | --- |
| MCP protocol | Official Python SDK | Custom JSON-RPC/session implementation | Keep official SDK and existing adapter file |
| OAuth | External issuer/introspection; host setup missing | Embedded signed tokens, DCR, owner-key login | Auth0 authorization-code + PKCE; verify RS256 JWTs with its public JWKS |
| Provider | Fixed `gpt-session` | Fixed `gemini-session` | Verified OAuth `azp` client ID mapped to exactly one provider |
| Owner identity | Pinned subject | Static keys or signed client subject | One pinned Auth0 owner `sub`; no login secret in gateway |
| Code replay | Delegated to issuer | In-memory `_used_codes` | Managed issuer owns code exchange/replay state; gateway accepts access JWTs only |
| Signing/login | Separate introspection secret | Signing seed can fall back to owner login/GM token | Auth0 retains signing private keys; gateway gets public keys only |
| Serialization | Per-instance thread RLock | Lock protects session map, not complete tool operations | Thread RLock plus Linux `flock` for entire worktree operation across processes |
| Refresh | Full public state | Compact state, hash and cursor checks | Compact default, opt-in full state, both refresh tool names call one handler |
| Read-only discovery | Writes listed but refused | Mutators omitted | Expose only public read/reference tools initially |
| Restart | Persistent disk required | Stateless/ephemeral hosting proposed | Persistent disk retained; safe fresh-clone recovery with write reapproval |

A direct reproduction of Gemini's original OAuth class returned token-exchange
HTTP **200**, repeated-code **400**, then **200 for that same code after restarting
the OAuth object**. Its fallback also derives the signing key from the owner login
secret. Neither behavior is imported. Gemini's `checkout -B` startup path is also
not imported: it could discard local unconfirmed work. The candidate never resets,
force-pushes or overwrites an existing worktree on startup.

## Storage verdict and recovery contract

Persistent storage is required for write-capable operation of the current gateway.
Git contains acknowledged tables, rolls, commit plans, events and publication state
because each acceptance checkpoints the whole scope before returning. But a process
can stop between local dice/state/log writes and its push. Those local journals and
unconfirmed commits must survive a normal restart. “Git is remote” does not make
every instruction before acknowledgement durable.

The local tests kill a subprocess with SIGKILL after a dice write, after a successful
roll push, and after remote acceptance with its acknowledgement lost. They also
delete the entire server clone and restore only from the bare remote. Retrying the
same request preserves the original result and leaves one logical roll record.
A partial ledger batch survives disk loss through its already-pushed immutable
commit plan and completes without asking a GM to re-author it.

After complete disk loss, **remote-accepted work has zero loss in these fixtures**.
Never-acknowledged, local-only work is not promised as a saved artifact: the test
reconstructs its same deterministic roll from the remote RNG state/request, without
an extra canonical roll. An unpushed free-form draft may require re-entry. This is
not a promise that an ephemeral disk can retain arbitrary unpushed bytes.

The worktree's `.git` directory holds a storage-generation marker. Normal restart
preserves it. A replacement disk has a new generation; the host's separately pinned
`GENESIS_STORAGE_GENERATION` no longer matches and **turn writes stay disabled**.
Read-only refresh can show remote recovery state, but an operator must compare
accepted receipts and approve the new generation before any later write enablement.
Dirty or locally-ahead worktrees stop startup for operator recovery; they are never
silently reset. Git remains canonical; the disk is the surviving work journal.

OAuth code replay is handled **outside the Render disk**, by Auth0's one-time-code
store. Gateway restart/disk loss cannot clear that store. Local tests verify that
authorization codes and HMAC tokens cannot authenticate this resource server before
or after verifier restart. Auth0's actual code-exchange/replay behavior is documented
by Auth0, but has **not been exercised against an owner tenant**. That is an external
integration gate, not a claimed local certification of Auth0.

## Owner setup after separate deployment approval

You do not need to install Docker, Python or Git on your phone for these steps.
The files are prepared at `development/gm_provider/deploy/`.

### 1. Create the identity settings

At `https://manage.auth0.com/`, create a Free tenant in the US. In **Settings**,
copy its **Domain**; the issuer is `https://` + that exact domain + `/`. This is
assigned to your account; do not use the sample domain from another guide.

In **User Management → Users → Create User**, create your owner login in the
default database connection. Choose a unique password and keep it in your password
manager. Copy that user's **User ID** from its profile (usually beginning `auth0|`),
not the email address. That is `GENESIS_MCP_SUBJECT`.

In **Applications → Applications**, create two separately registered OAuth clients:
`Genesis ChatGPT` and `Genesis Gemini` (Regular Web Application, authorization-code
and refresh-token grants). Their **Client IDs** are public binding values. Their
**Client Secrets** go only into the corresponding ChatGPT/Gemini connection setup,
not into this gateway or this conversation. The server mapping is:

```json
{"COPY_CHATGPT_CLIENT_ID":"gpt-session","COPY_GEMINI_CLIENT_ID":"gemini-session"}
```

Copy the actual IDs from those two application settings to replace the keys. Use
pre-registered client credentials in both native-client setup flows, rather than
unrestricted DCR: unknown client IDs are refused by the gateway. In each app's
**Allowed Callback URLs**, add only the exact callback displayed by its respective
ChatGPT/Gemini connection wizard. Do not guess callback paths or use wildcards.
Use authorization-code with S256 PKCE; disable password/client-credentials grants.
Keep owner signup disabled or constrained; the gateway also pins the owner User ID.

### 2. Create the read-only Render service

At `https://dashboard.render.com/`, connect your GitHub account and select **New →
Blueprint** with repository `AustinFnFordham/Genesis-Protocol-Dev`, branch
`dev/shared-mobile-gateway-reconciled`. Set the Blueprint path to
`development/gm_provider/deploy/render.yaml`. Review the single Starter service
and 1 GB disk; do not add Postgres, Redis or any other database. Auto-deploy is off.

The Blueprint asks for these values:

| Render variable | Where you obtain it |
| --- | --- |
| `GENESIS_MCP_ISSUER` | Exact Auth0 tenant Domain from step 1, prefixed `https://`, suffixed `/` |
| `GENESIS_MCP_SUBJECT` | Owner User ID from Auth0 User Management |
| `GENESIS_MCP_CLIENT_PROVIDERS` | JSON mapping of the two Application Client IDs from step 1 |
| `GENESIS_GITHUB_TOKEN` | GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens; select this repository only, Contents **Read-only** for initial deployment; paste into Render's secret field |

The token is server-held, never embedded in a URL or given to either model. Render's
GitHub source-build connection does not by itself supply runtime Git credentials.
No `GENESIS_GM_TOKENS` are needed for initial reads. Keep
`GENESIS_MCP_ENABLE_WRITES=0`. Do not pin a storage generation or add GM write
credentials yet. The first release advertises no claim, context, dice or commit tools.

Render assigns the service a public **onrender.com URL**, shown at the top of its
service page. Copy that exact URL. The start command obtains it automatically as
`RENDER_EXTERNAL_URL`; the MCP resource is that URL plus `/mcp`. No DNS purchase or
custom domain is required. The server opens the existing shared scope in a separate
clone at `/var/data/authority/staging/shared-1`, without creating a new campaign.

### 3. Finish Auth0 API registration

In Auth0 **Applications → APIs → Create API**, name it `Genesis staging`, set the
**Identifier** to the exact Render MCP resource URL from step 2, and select RS256.
Add permission `genesis:read` only for this first release. Set access-token lifetime
to 900 seconds. Enable offline access/refresh-token rotation if those options are
used by the clients. JWT access tokens can remain usable until expiry after consent
revocation; the 15-minute lifetime bounds that window.

In tenant **Settings → Advanced**, enable **Resource Parameter Compatibility
Profile**, so MCP's `resource` selects this API audience instead of the userinfo
audience. Keep your two pre-registered client applications; no open registration is
needed. If that setting or S256 support is unavailable on your tenant, stop and
report it instead of weakening audience/PKCE validation or selecting no-auth.

Your gateway holds **no Auth0 private signing key and no owner password**. Auth0
hosts login/consent and keeps code-replay state. The gateway fetches public JWKS
from the exact configured issuer. Only valid issuer/audience/expiry/scope/owner
tokens whose signed `azp` matches the pinned client map are accepted.

### 4. Connect ChatGPT and Gemini

On ChatGPT web, open `https://chatgpt.com/plugins` → plus → **Add custom MCP server**.
Name it Genesis, enter the exact Render `/mcp` URL, choose OAuth, and enter only
the `Genesis ChatGPT` client credentials. Complete your Auth0 owner login and
consent. Copy the exact callback from this wizard into that Auth0 application's
allowlist if needed, then retry connection. Install the resulting plugin.

In a mobile browser, open `https://gemini.google.com/` → **Settings → Connected
Apps → Add a custom app**. Some accounts show this under Personal Intelligence or
Developer Mode. Enter the same `/mcp` URL. Open **Advanced features / Show more**
and enter the `Genesis Gemini` client credentials. Copy its displayed callback into
only that Auth0 application's allowlist. Complete the same owner's Auth0 login.
If a wizard does not display a callback, use its official connection settings/help
to obtain it; do not guess a Google callback URL.

Both connections must use OAuth, never the GitHub token, a server signing key, a
static shared owner key, or “No authentication.” Account eligibility and UI wording
are external checks; setup is not proof of native app invocation.

### 5. Prove both native apps before discussing writes

In the native ChatGPT app, select Genesis and send:

> Use Genesis only to call genesis_refresh. Report connection_provider, campaign ID,
> revision, ledger head, public_sha256 and pending request. Do not claim or modify a turn.

Repeat in the native Gemini app, using `genesis_staging_refresh` or `genesis_refresh`.
Expand each app's actual tool call. Save the two public receipts. The providers must
be `gpt-session` and `gemini-session`; campaign, revision, head and digest must match
if the campaign did not move. Compare them with an independent read. Inspect the
remote staging ref and assert no action/lease/roll/operation/ledger changes occurred.
At present the known queue is `shared-0002`, submitted for `gpt-session`, with no
lease holder; do not treat that historical pointer as a substitute for the real refresh.

Do not enable writes until both native calls and the real Auth0 replay/PKCE tests
pass and you separately authorize gameplay. Later enabling requires the host switch,
`genesis:gm` consent, server GM tokens for both providers, runtime Git write rights,
and the reviewed storage generation. Each is independently required; tool arguments
cannot select or impersonate a provider. No enablement is authorized by this proposal.

## Commands and validation boundaries

The Docker image's exact start command is:

```sh
python3 -B development/gm_provider/deploy/start.py
```

`PORT` and `RENDER_EXTERNAL_URL` are supplied by Render. The entrypoint binds
`0.0.0.0:$PORT`, drops to uid/gid 10001 before running Git or serving requests,
mounts authority under `/var/data`, clones only if missing and otherwise uses
fast-forward-only synchronization. It never runs `checkout -B`, reset or force-push.
The Blueprint was validated against Render's published JSON schema. The boot
function was executed against a local bare remote and tested to preserve dirty and
ahead worktrees. SDK transport, discovery, OAuth-token verification and two-client
refresh were exercised over a real local TCP listener with test signing keys.

The following official validation/build commands are prepared:

```sh
render blueprints validate development/gm_provider/deploy/render.yaml
docker build -f development/gm_provider/deploy/Dockerfile -t genesis-shared-mobile-candidate .
```

Docker/Podman and the Render CLI are not installed in this executor, and no Render
account token is exposed. Therefore the Docker image build and Render CLI/API
account-level validation were **not run**. Local schema validation and executed
entrypoint tests are not represented as a successful container build or deployment.
The approved first Render build is still a release check; stop on any build failure.

Local evidence: **69 unittest cases passed**, plus the NPC-review script, in seven
scoped suites. The latest reconciled suite (14 cases) took 13.98 seconds; retained
MCP suite (8) 3.91 s; Git diagnostics (15) 2.45 s; shared Git store (4) 17.31 s;
gateway (23) 31.80 s; HTTP service (5) 11.34 s. Runs used isolated fixtures; these
durations are not remote latency measurements. Full logs, deployment checks,
original-code replay reproduction and protected-file hashes are saved under
`verification/shared-mobile-reconciliation/`. This was not a full repository or
browser regression run; no player UI was changed.

Useful Gemini scenarios were retained as behavioral tests: compact refresh and
cursor/digest checks, public/private filtering, local HTTP framing, provider-routing
refusal and a scripted complete GM turn. Its embedded DCR/PKCE tests were not
copied as if that OAuth server remained authoritative; JWT validation/restart tests
replace resource-server cases, and the real managed-issuer code/PKCE exchange
remains an explicit external gate. GPT's existing transport, lease, idempotency,
privacy and diagnostic regressions continue to pass.

## Limits, recovery and rollback

Only the existing noncanonical shared-1 scope is opened. One worker/instance owns
one persistent worktree, and every tool operation takes its OS file lock. External
writers still face the original Git CAS and gateway lease checks; no engine or
Claude-runtime change is required. Rules, deterministic dice, append-only ledger,
paginated publication and private/public projections are reused.

For a restart, retain the volume and accepted receipts. For dirty/ahead startup,
stop and reconcile the exact accepted request; never delete leases or reset Git.
For complete disk loss, stop writes, clone the staging ref and inspect recovery
and accepted receipts. The changed storage generation prevents automatic write
resumption. Do not restore an old disk snapshot and assume it is current authority.

Rollback means disabling this staging listener or reverting the deployment's code
version while retaining its disk and remote history. No canonical campaign rollback,
lease deletion, reroll or force-push is part of rollback. Neither original adapter
branch nor diagnostic repair `6942257` is changed.

Private GM context is still inspectable by the owner of a GM chat; public refresh
and pages stay filtered. An adversarial player who must not inspect GM payloads
needs a separate GM-only channel/account. No claim of secret-from-owner chat exists.

Sources: https://render.com/docs/disks ; https://render.com/docs/blueprint-spec ;
https://render.com/pricing ; https://auth0.com/pricing ;
https://auth0.com/ai/docs/mcp/overview ;
https://support.auth0.com/center/s/article/auth0-oauth-2-0-authorization-code-expiry-time-and-one-time-use-controls ;
https://support.auth0.com/center/s/article/mcp-audience-error-with-auth0 ;
https://developers.openai.com/plugins/build/auth ;
https://developers.openai.com/api/docs/guides/custom-mcp-server ;
https://support.google.com/gemini/answer/17209137 .
