# Open Genesis on iPhone, iPad or Windows

**One place to bookmark:** https://github.com/codespaces/glowing-space-xylophone-65qvxqp9pvc54qq

Use ordinary **Safari** on iPhone/iPad, or **Edge/Chrome** on Windows. If ChatGPT shows a file/download view,
copy the link and paste it into Safari's address bar; do not save the .dev address as a file.

1. Open that workspace link and sign into GitHub in that same browser. Resume **glowing space xylophone** if it
   has stopped; wait for the editor to connect. Do not create a second Codespace.
2. The preview startup hook should report **READY**. If needed, editor menu → Terminal → Run Task →
   **Genesis: Start or check private preview**. This task is safe to run repeatedly; no terminal typing is needed.
3. Open the editor's **Ports** panel, find **8080 / Genesis dev preview**, verify **Private**, then choose
   **Open in Browser**. Its canonical preview URL is:
   https://glowing-space-xylophone-65qvxqp9pvc54qq-8080.app.github.dev/
4. Check the gold **Genesis Development / Test Environment · M12** banner and **Sim Deck: Drill Seven
   (mobile-test-1)**. The intent-first M11 builder remains. Nothing here is Hask Meadow.

If GitHub asks you to sign in again, complete the ordinary sign-in in the same browser and reopen 8080 from Ports.
Private-port authorization is separate from the GitHub repository connector. Do not bookmark a /pf-signin,
/auth/postback or callback URL containing query parameters; those are temporary authorization redirects.
Do not change the port to public, disable Safari cookie protections, add a paid budget, or create another host.

## Startup hook already applied
On 2026-11-20 this existing Codespace was updated to integration `46e935d` and normally rebuilt.
Automatic startup reported READY, repeated starts succeeded, and 8080 remained Private. No one-time terminal
setup or second Codespace is needed. Use the task in step 2 if recovery is needed.

For future updates, preserve local work, confirm the integration branch and use `git pull --ff-only`.
A changed devcontainer lifecycle configuration requires **Codespaces: Rebuild Container** once.
The launcher refuses an occupied unrecognized port; inspect the process before stopping anything.

Last-resort single command, from `/workspaces/Genesis-Protocol-Dev`:

```bash
python3 -B development/preview/manage_preview.py start
```

If PyYAML is missing, run `python3 -m pip install -r development/preview/requirements.txt` once, then rerun the task.
If the port is occupied by an unrecognized server, stop and inspect it; do not kill arbitrary processes.

## Try the fixture
- Select a plan, edit the custom primary action, and expand **Full mechanics catalog** to combine speech/movement.
- Taunt requires a target and exact words. Costs still come from the shared validator.
- A submitted turn must report **Preview only: no GM is attached**. The literal declaration stays in browser state.
- WHISPER review is explicitly a simulated sample; edit/accept/reject changes only this browser's simulation.
- **Features and limits → diagnostics** shows the noncanonical evaluator fixtures.
- **Reset preview state** clears this preview's simulation/drafts, not campaigns, other websites or unrelated keys.

Drafts persist in this browser, not across devices; they are not cloud-synced. Private browsing or clearing website
storage can remove them. No offline gameplay is supported. On iOS, Safari → Share → Add to Home Screen can create
an optional bookmark; it opens through the browser/authentication flow. Native installation/auth behavior is unverified.

## Free usage and sleep
Keep paid Codespaces usage blocked. The account had a $0 budget at creation; recheck current usage/budgets before
extended sessions. Compute runs while the Codespace is active, including idle time until its configured timeout;
stop it at https://github.com/codespaces when finished. Stopped Codespaces still consume storage allowance.
If GitHub says free allowance is exhausted, stop and wait for renewal. Do not raise the budget or add billing.

## If it still downloads or does not open
See `M12_ACCESS_REPORT.md`. Exact cause of the original iPhone download remains unproven. Record browser/device
version, whether you used Safari or an in-app view, and a screenshot without auth URL query parameters. Native
Safari on the owner's physical iPhone/iPad must still be checked; viewport/WebKit emulation is not equivalent.
