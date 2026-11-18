# Private iPad development preview

This runs the existing Datapad with Sim Deck: Drill Seven (`mobile-test-1`), a noncanonical public fixture.
No GM is attached. Turn submission is stored in browser localStorage and explicitly fails as preview-only;
WHISPER answers use a clearly simulated local review. No gateway credentials, hidden campaign data or live writes.

## Working private preview (verified 2026-11-18)
- Preview: https://glowing-space-xylophone-65qvxqp9pvc54qq-8080.app.github.dev/
- Editor: https://glowing-space-xylophone-65qvxqp9pvc54qq.github.dev/
- Existing codespace: **glowing space xylophone**, personal owner AustinFnFordham, 2 cores / 8 GB RAM.
- Branch: `integration/tb4-whisper-v01`; M11 integration `d6b3b50`, with verified preview grant fix `337bfae`.
- Port **8080 / Private** was observed in the editor, with the documented Python preview process.
- At creation, GitHub showed 120 included core-hours and 15 GB storage, both unused, and a $0 Codespaces budget
  with paid usage blocked. No payment method, budget, or billing setting was changed. Recheck remaining allowance
  before later use; this codespace consumes the shared free allowance. It is not an always-on service.

Open the Preview link in iPad Safari while signed into your GitHub account. If it has gone to sleep, resume the
existing codespace at https://github.com/codespaces, wait for the editor to connect, then reopen the Preview link.
Do not create a second codespace to restart this one. Stop it from the Codespaces page when finished.

## Start on iPad
1. Prefer the existing preview above. If recreating it is necessary, sign into your own GitHub account in Safari,
   open this repository and select the verified branch `integration/tb4-whisper-v01`.
2. Before creating anything, check GitHub Settings → Billing and licensing → Usage/Budgets for your personal
   Codespaces allowance. Keep paid usage blocked. If included compute or storage is exhausted, stop;
   do not add a payment method, increase a budget, or enable a paid overage for this preview.
   GitHub Free includes 120 core-hours (=60 running hours at 2 cores) and 15 GB-month storage;
   other codespaces share that allowance. A stopped codespace still consumes storage.
3. Repository → Code → Codespaces → create on this branch; choose the **2-core** machine and personal billing owner.
   Do not proceed if GitHub requires payment or shows unavailable free allowance.
4. Wait for the Python devcontainer to finish. It installs the pinned preview dependency and starts port **8080**.
5. Open the editor's **Ports** tab. Verify 8080 has **Private** visibility. Keep it private, then choose Open in Browser.
   Use GitHub's supplied URL; a recreated codespace has a different hostname from the verified one above.
6. Verify the gold **Genesis Development / Test Environment** banner names M11 and `mobile-test-1`.
   Try a suggested plan; edit the Custom primary action; expand the Full mechanics catalog to combine movement,
   speech, Taunt or other supporting activities. The shared validator still checks the complete declaration.
7. Open Features and limits → diagnostics. Try the sample WHISPER review. A normal submitted turn must say
   **Preview only: no GM is attached**. If you see live Hask Meadow or a real worker connection, stop.

## Restart after travel or sleep
1. Open https://github.com/codespaces in Safari and resume the existing codespace. Do not create another each time.
2. The first real Codespace did not leave the automatic preview process running. The following manual recovery
   was verified. If the link does not load, open Terminal in the editor at `/workspaces/Genesis-Protocol-Dev`:
   ```bash
   python3 -m pip install -r development/preview/requirements.txt
   python3 -B development/preview/serve_preview.py --host 0.0.0.0 --port 8080
   ```
   If it says address already in use, the first preview is already running: use Ports → 8080.
3. Reopen its **private** forwarded URL while signed into GitHub. Stop the codespace when finished to save compute.
4. To update code, first check `git status` and preserve any changes. Verify `git branch --show-current` is
   `integration/tb4-whisper-v01`; stop if it is another branch. With a clean codespace on the integration branch:
   `git pull --ff-only`, rebuild the Datapad (`python3 -B campaigns/starwars_litrpg/ui/build_datapad.py`), then restart
   the preview process. If a conflict appears, stop and ask for development recovery; never reset campaign history.
5. Browser-local preview state survives reloads. Features and limits → Reset preview state resets only the simulation.

## Verification boundary
The owner completed secure Google and GitHub device verification; GitHub then created this Codespace through its
normal UI. The hosted real Datapad loaded, with M11 and the fixture name in its banner. Plan selection, custom primary
and secondary text, collapsed/expanded catalog, simulated submission, WHISPER edit, diagnostics and reset were exercised.
The combined declaration retained the exact text, returned the explicit no-GM message and left fixture revision 4 /
evt_0006 unchanged. The original M11 remote workflow passed all 58 suites plus the functional DOM check. The preview follow-up also
passed all 58 suites, and its corrected independent custom-plan DOM case passes locally. Hosted Taunt was checked
with missing-target rejection and legal preflight after entering target and exact words. This is real
Chromium and hosted-preview evidence; native iPad Safari interaction still requires the owner's test. The preview
does not advance the separately hosted mobile-test campaign or Hask Meadow.

References: https://docs.github.com/en/billing/concepts/product-billing/github-codespaces
and https://docs.github.com/en/codespaces/troubleshooting/troubleshooting-included-usage
