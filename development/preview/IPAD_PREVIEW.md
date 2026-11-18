# Private iPad development preview

This runs the existing Datapad with Sim Deck: Drill Seven (`mobile-test-1`), a noncanonical public fixture.
No GM is attached. Turn submission is stored in browser localStorage and explicitly fails as preview-only;
WHISPER answers use a clearly simulated local review. No gateway credentials, hidden campaign data or live writes.

## Start on iPad
1. Sign into your own GitHub account in Safari. Open this repository and select the verified M11 branch
   `dev/m11-intent-first-work` (use `integration/tb4-whisper-v01` only after the M11 verification merge).
2. Before creating anything, check GitHub Settings → Billing and licensing → Usage/Budgets for your personal
   Codespaces allowance. Keep paid usage blocked. If included compute or storage is exhausted, stop;
   do not add a payment method, increase a budget, or enable a paid overage for this preview.
   GitHub Free includes 120 core-hours (=60 running hours at 2 cores) and 15 GB-month storage;
   other codespaces share that allowance. A stopped codespace still consumes storage.
3. Repository → Code → Codespaces → create on this branch; choose the **2-core** machine and personal billing owner.
   Do not proceed if GitHub requires payment or shows unavailable free allowance.
4. Wait for the Python devcontainer to finish. It installs the pinned preview dependency and starts port **8080**.
5. Open the editor's **Ports** tab. Verify 8080 has **Private** visibility. Keep it private, then choose Open in Browser.
   The actual URL is supplied by GitHub; no working URL has been created or verified in this Work session.
6. Verify the gold **Genesis Development / Test Environment** banner names M11 and `mobile-test-1`.
   Try a suggested plan; edit the Custom primary action; expand the Full mechanics catalog to combine movement,
   speech, Taunt or other supporting activities. The shared validator still checks the complete declaration.
7. Open Features and limits → diagnostics. Try the sample WHISPER review. A normal submitted turn must say
   **Preview only: no GM is attached**. If you see live Hask Meadow or a real worker connection, stop.

## Restart after travel or sleep
1. Open https://github.com/codespaces in Safari and resume the existing codespace. Do not create another each time.
2. Port 8080 should restart automatically. If not, open Terminal in the editor:
   ```bash
   python3 -m pip install -r development/preview/requirements.txt
   python3 -B development/preview/serve_preview.py --host 0.0.0.0 --port 8080
   ```
   If it says address already in use, the first preview is already running: use Ports → 8080.
3. Reopen its **private** forwarded URL while signed into GitHub. Stop the codespace when finished to save compute.
4. To update code, first check `git status` and preserve any changes. With a clean codespace on the M11 branch:
   `git pull --ff-only`, rebuild the Datapad (`python3 -B campaigns/starwars_litrpg/ui/build_datapad.py`), then restart
   the preview process. If a conflict appears, stop and ask for development recovery; never reset campaign history.
5. Browser-local preview state survives reloads. Features and limits → Reset preview state resets only the simulation.

## Verification boundary
ChatGPT Work's GitHub connector can read/write development source but exposes no Codespaces lifecycle or billing API.
The browser was signed out at GitHub's Codespaces login redirect. No credentials were requested, no Codespace was
created, and no allowance or private forwarded port was verified. Local HTTP returns 200 for the real preview and
its diagnostics; functional DOM checks pass. Real Chromium regression and iPad Safari verification remain separate
checks (see the progress report). No private preview link is claimed until that workflow is actually exercised.

References: https://docs.github.com/en/billing/concepts/product-billing/github-codespaces
and https://docs.github.com/en/codespaces/troubleshooting/troubleshooting-included-usage
