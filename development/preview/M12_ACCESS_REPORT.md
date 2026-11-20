# M12 — access evidence and verification boundary

Base integration: `23ba53d203708515658a115c524a8aa5d646c7ad`; live observed `1792078eb6ed12a6a4697b709228dd4450c1439b`.
M0–M11 are preserved. Branch: `dev/m12-cross-platform-access`. No campaign turns or live deployment.

## What is established
- On 2026-11-20 the existing personal Codespace was listed Active, integration branch, 2 cores, 2.25 GB storage.
- Its terminal reported checkout `337bfae` and port 8080 returned connection refused before repair.
- The preview URL observation in Work was refused by the browser URL-policy gate with an unsupported-protocol
  error before response inspection. This is an executor observation restriction, not evidence of a Safari defect.
- M11's server is Python SimpleHTTPRequestHandler: an existing, nonempty index normally has text/html MIME.
  There is no source evidence that the running M11 app intentionally sends an attachment or octet-stream response.
- Exact cause of the owner's original zero-byte download is NOT established: no original response/redirect trace,
  iOS browser version, or physical-device session was available. A missing process is an observed current defect,
  not retrospective proof of that download's cause.

## Repairs
- Idempotent Linux launcher with serialized start, real health check, detached process, stable log and workspace
  identity. Occupied unrelated/legacy ports fail closed; no arbitrary process kill. Explicit working directory.
- Editor task and postStart hook use the same command. Existing Codespace needs one rebuild to adopt changed
  devcontainer lifecycle hooks; task/manual recovery works without creating another environment.
- HTTP root and index return nonempty UTF-8 text/html, Content-Length, inline disposition and no-store. HEAD has
  zero body by HTTP definition but the same nonzero Content-Length. Missing output produces HTML 503; bad paths 404.
- Fixed route allowlist prevents directory or checkout exposure. Atomic output replacement prevents truncation
  while rebuilding. These headers apply AFTER GitHub authorization; they cannot fix a GitHub-owned redirect.
- 44px disclosure/option controls, 16px selects, wrapping and safe-area/short-landscape handling; scroll position,
  input focus/caret and immediate draft persistence. Simulated WHISPER edit drafts persist on reload.
- Preview-only storage namespace; reset clears simulation and its draft/preferences, preserving unrelated keys.
- Local manifest/icon with display=browser. No service worker, offline gameplay, installed authentication token or
  standalone-mode cookie dependency. Home Screen bookmark behavior remains a physical-device check.

## Client boundary
The preview is still a fixture-only Datapad with browser-local simulated submissions and review responses.
No GM, deterministic game rolls, campaign ledger writes, model calls, hidden GM data or remote gateway is attached.
The authoritative Atomic validator, sequencer and Taunt mechanics are unchanged.

## Test matrix
Results are filled after verification; do not treat a pending row as a pass.

| Runtime | Sizes / interaction | Status |
|---|---|---|
| Linux Chromium | iPhone 390x844 / 320x568 / 844x390; iPad 820x1180 / 1180x820; desktop 1440x900; touch/keyboard | Pending remote CI |
| Linux WebKit | Same viewport/touch workflows | Pending remote CI; NOT native Safari |
| Windows Chrome | Same responsive workflows on hosted Windows runner | Pending remote CI; NOT owner's Windows PC |
| Physical iPhone Safari | Auth redirects, download symptom, browser chrome, real keyboard | Pending owner verification |
| Physical iPad Safari | Both orientations, Magic Keyboard, safe areas | Pending owner verification |

Local Chromium download is blocked by HTTP 403 from the browser CDN. Installed system Chromium also failed to
launch in this executor. Local DOM/HTTP tests are kept separate from browser-engine evidence.

## Owner evidence needed if it still downloads
Open the workspace first in ordinary Safari, sign into GitHub there, wait for the existing environment, then open
its private 8080 port from Ports. Record iOS version, whether the link opened inside ChatGPT or Safari, last safe
hostname/path (omit query parameters), screenshot of the error/download label, and time. Do not send cookies,
passwords, email codes, auth URLs or HAR files with credentials. Never make the port public or disable Safari
privacy protections as a diagnostic shortcut.

Sources: GitHub documents private-port authentication cookies with a 3-hour expiry at
https://docs.github.com/en/codespaces/reference/security-in-github-codespaces .
That supports expiration as a hypothesis, not an established cause for this incident.
