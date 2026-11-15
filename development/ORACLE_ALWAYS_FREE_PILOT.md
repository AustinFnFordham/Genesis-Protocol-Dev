# Genesis Oracle Always Free pilot — $0/month target, not deployed

This replaces the paid Render proposal. Base commit 09a3094 remains intact.
The adapter, Auth0 authentication, provider bindings, Git CAS, process locking,
accepted-work recovery, dice and ledger code are unchanged. Only hosting preparation
is added. There are no model API calls, new campaign database, or paid fallbacks.

## Verified limits and blockers

Oracle's current Free Tier page lists A1 allowances of 1,500 OCPU-hours and
9,000 GB-hours/month (2 OCPUs/12 GB equivalent). Its Arm page still lists double
those amounts. This plan fits BELOW BOTH; the owner's console quotas remain an
additional required check. Storage allowance: 200 GB combined boot/block and five
combined volume backups, in the home region. Internet egress: first 10 TB/month.
Never count temporary trial credits as free capacity.

Signup requires an eligible credit/debit card. Oracle documents a $1 authorization
hold, reversed by Oracle immediately; banks can take several days. Holds may recur.
If a temporary hold is unaffordable, this option cannot satisfy that constraint.
One free account per person; no duplicate-account workaround. Stay Free Tier: never
click Upgrade or Pay As You Go. Existing resources count toward all allowances.

Capacity is NOT guaranteed. If A1 is unavailable, try another availability domain
in the SAME home region or wait. Do not choose A2, another paid shape, another region,
or upgrade. Idle instances may be reclaimed after seven days of low utilization;
accounts inactive for 30 days may be suspended/terminated. There is no free uptime
SLA. Uninterrupted 24/7 availability cannot be promised at $0.

## Application sizing evidence

Before workspace maintenance, actual application fixtures were profiled on x86_64,
CPython 3.12.14 / Node 24.22.1, with deployment-version dependencies:

| Workload | Sampled process-tree RSS peak | User/system CPU | Wall time |
| --- | --- | --- | --- |
| Two authenticated MCP client refreshes, local TCP | 70.66 MiB | 0.8221 / 0.0523 s | 1.113 s |
| Scripted deterministic turn on a disposable fixture | 98.50 MiB | 1.4149 / 0.1372 s | 1.637 s |

RSS was sampled at 20 ms and may double-count shared pages. OS and Caddy were not
included. These are NOT A1 benchmarks or a live GM turn. All 30 Python dependencies
resolved as ARM64-compatible wheels, including cryptography, cffi, pydantic-core,
rpds and PyYAML; a hash-checked ARM installation dry-run succeeded. ARM execution
has not been tested. Scratch maintenance removed those intermediate wheel/log
files; these numbers are the observed transcript results, not newly rerun artifacts.
Current saved tests have fresh logs in verification/oracle-free-pilot/.

Select ONE VM.Standard.A1.Flex, 1 OCPU, 2 GB RAM, Ubuntu 24.04 ARM64. That leaves
headroom for Linux and Caddy without oversizing. A 31-day month uses at most 744
OCPU-hours and 1,488 GB-hours. No GPU, local model, x86-only application binary or
container runtime is required. Do not select the 8-GB Cloud Developer image.
A1 native dependency installation and memory under real traffic remain pilot gates.

## Numbered owner setup — execute only after deployment approval

1. **Account and region.** Open https://signup.cloud.oracle.com or use your existing
   Oracle Free Tier account. New account: choose US East (Ashburn) if offered;
   existing account: use its established home region. Check Billing → Upgrade and
   Manage Payment: do NOT upgrade. Record the home region. Under Limits, Quotas
   and Usage, confirm room for this pilot and that it qualifies without trial credits.
   A1 sometimes lacks a generic free badge: verify its explicit free allowance.
   If free eligibility cannot be established, stop before Create.

2. **Create only this configuration.** Compute → Instances → Create:
   name `genesis-staging-free`; image Canonical Ubuntu 24.04, ARM64, Always Free
   eligible; shape `VM.Standard.A1.Flex`; **1 OCPU, 2 GB**; boot volume **50 GB**,
   default eligible performance. Save the generated SSH private key securely.
   Use a public subnet in a VCN with Internet Gateway; assign one ephemeral public
   IPv4. Do not add NAT Gateway, load balancer, marketplace image, database,
   cross-region replication or optional paid services. Do not enable higher volume
   performance. A nonzero net charge or uncertain eligibility is a stop condition.

3. **Persistent volume.** Create a separate **50 GB Always Free block volume** in
   the same availability domain/home region; attach it using Paravirtualized mode.
   Total planned storage is 100 GB, leaving capacity for retained recovery boots.
   Count any existing volumes too. Keep volume deletion-on-termination disabled.
   Do not select an automatic backup policy that could exceed the five-backup limit.
   Record instance OCID, volume OCID and public IP from their details pages.

4. **Network.** In the subnet security list/NSG permit TCP 80 and 443 from
   `0.0.0.0/0`, TCP 22 only from your current trusted IP `/32`, and normal outbound
   DNS/HTTPS access. Never expose 8789 or Caddy's administration port 2019.
   OCI security rules and the VM firewall must both permit the traffic. No additional
   paid network component is needed. Review your existing VCN rather than opening
   every port. Cloud Shell is a free, quota-limited browser terminal; use it or an
   SSH client to connect as `ubuntu` using the command/key shown by OCI. Do not
   host the gateway inside Cloud Shell.

5. **Mount safely.** On the VM run `lsblk -f`. Obtain the newly attached data-device
   path from OCI's attachment page and match its size/identity. Only for a confirmed
   NEW EMPTY data volume, run `sudo mkfs.ext4 -L genesis-data DEVICE_PATH`.
   Never format the boot device or a restored volume. Use `sudo blkid DEVICE_PATH`
   to obtain its UUID, create `/var/data`, and add this line to `/etc/fstab`:
   `UUID=ACTUAL_UUID /var/data ext4 defaults,nofail 0 2`.
   Run `sudo mount /var/data`, then `findmnt /var/data`. If restoring, mount the
   existing filesystem without formatting. The gateway refuses an unmounted path.

6. **Free hostname.** Sign in at https://www.duckdns.org and register an available
   subdomain, for example a unique variant of `genesis-austin-pilot`. Set its IPv4
   to the VM public IP; leave IPv6 unset unless deliberately configured. The full
   assigned name, e.g. `YOURNAME.duckdns.org`, costs no domain purchase. Keep the
   DuckDNS login/token private. This pilot uses dashboard DNS updates, so no DNS
   token needs to be stored on the VM. Verify its A record matches the OCI IP.
   The endpoint will be `https://YOURNAME.duckdns.org/mcp`, not the raw IP.

7. **Install code and prerequisites.** These commands are for the approved VM:

   ```sh
   sudo apt-get update
   sudo apt-get install -y git python3-venv nodejs curl ca-certificates gnupg debian-keyring debian-archive-keyring apt-transport-https
   sudo git clone --branch dev/oracle-always-free-pilot https://github.com/AustinFnFordham/Genesis-Protocol-Dev.git /opt/genesis-code
   # Pin the code to the full candidate SHA supplied in the completion receipt:
   sudo git -C /opt/genesis-code checkout --detach CANDIDATE_SHA_FROM_RECEIPT
   sudo groupadd --gid 10001 genesis
   sudo useradd --uid 10001 --gid 10001 --home-dir /var/lib/genesis --create-home --shell /usr/sbin/nologin genesis
   sudo chown genesis:genesis /var/data
   sudo python3 -m venv /opt/genesis-venv
   sudo /opt/genesis-venv/bin/pip install --only-binary=:all: -r /opt/genesis-code/development/gm_provider/requirements-mcp.txt PyYAML==6.0.3
   uname -m
   node --version
   ```

   Expect `aarch64`, Python 3.12 and Node 18 or later. Do not run x86 binaries or
   compile unavailable native dependencies as a fallback. If the binary-only install
   fails on the actual VM, stop and report it. Install Caddy from its official Ubuntu
   package instructions at https://caddyserver.com/docs/install#debian-ubuntu-raspbian
   (free package; standard modules only). Stop its default service until configured.

8. **Reuse managed authentication.** Keep the Auth0 Free tenant, owner User ID,
   and two registered client IDs from the reconciled guide. If not created, obtain
   them from Auth0 Dashboard → tenant Settings, User Management → Users, and
   Applications → Applications. Keep client secrets only in the respective ChatGPT
   and Gemini OAuth setup. Use the included Auth0 tenant domain, not a paid custom
   domain. Register the exact DuckDNS `/mcp` URL as the API Identifier (RS256), grant
   only `genesis:read`, and enable Resource Parameter Compatibility Profile.
   Keep S256 PKCE and exact callback allowlists from each client's setup wizard.
   Do not use owner passwords as server signing keys. No paid Auth0 plan is authorized.

9. **Protected configuration.** Create `/etc/genesis` and use `sudoedit` to create
   root-owned, mode-0600 `gateway.env`, using the supplied example. Replace resource,
   issuer, owner User ID, and the two client-ID mapping keys with values from steps
   6/8. Keep `GENESIS_MCP_ENABLE_WRITES=0`; do not add GM tokens or a storage-generation
   approval. If Git reads require authentication, add only a server-held repository
   Contents: Read token. Never paste credentials into chat or a Git URL.
   Create `/etc/genesis/public.env` containing only
   `GENESIS_HOSTNAME=YOURNAME.duckdns.org` (the actual hostname, no angle brackets).

10. **Stage and validate services.** Run:

    ```sh
    sudo install -d -m 0755 /etc/genesis /etc/systemd/system/caddy.service.d
    sudo install -d -o caddy -g caddy -m 0700 /var/data/caddy
    sudo install -m 0644 /opt/genesis-code/development/gm_provider/deploy/oracle/genesis-gateway.service /etc/systemd/system/
    sudo install -m 0644 /opt/genesis-code/development/gm_provider/deploy/oracle/Caddyfile /etc/caddy/Caddyfile
    sudo install -m 0644 /opt/genesis-code/development/gm_provider/deploy/oracle/caddy-override.conf /etc/systemd/system/caddy.service.d/genesis.conf
    sudo chmod 0600 /etc/genesis/gateway.env /etc/genesis/public.env
    sudo systemd-analyze verify /etc/systemd/system/genesis-gateway.service
    sudo systemctl daemon-reload
    ```

    On the default OCI Ubuntu firewall, also persist the two required ports:

    ```sh
    sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
    sudo iptables -I INPUT 1 -p tcp -m multiport --dports 80,443 -j ACCEPT
    sudo netfilter-persistent save
    ```

    Keep the OCI NSG/security-list rules from step 4 too. Do not flush existing rules.
    Caddy reads the public hostname via its environment file. Its state/certificates
    live on the retained volume. It issues/renews Let's Encrypt certificates using
    ports 80/443; there is no certificate purchase. TLS issuance and the ARM-host
    service start have NOT been exercised here. After deployment approval and these
    checks, start the pilot with `sudo systemctl enable --now genesis-gateway caddy`.
    Check `systemctl status genesis-gateway caddy` and protected server logs locally.
    Never post credential-bearing logs or GM context to a public issue.

11. **Verify HTTPS and authentication.** From outside the VM, GET
    `https://YOURNAME.duckdns.org/.well-known/oauth-protected-resource/mcp`: expect
    JSON with the exact resource and Auth0 issuer. A POST to `/mcp` without a token
    must return 401 and an OAuth challenge. Certificate verification must succeed
    normally: do not use `curl -k` or no-auth. Backend 8789 must be unreachable publicly.

12. **Native mobile proof.** Connect/install Genesis on ChatGPT web and in Gemini's
    custom Connected Apps settings using the same `/mcp` URL and each client's own
    OAuth registration. Follow the Auth0 account/callback steps in the reconciled
    guide, replacing Render's URL with DuckDNS. In EACH native mobile app call only
    `genesis_refresh` (Gemini may use its alias `genesis_staging_refresh`). Save actual
    tool receipts: connection_provider, campaign ID, revision, head, public_sha256,
    pending request and lease state. Expect distinct provider bindings and matching
    public cursors if authority did not move. Check the staging Git ref and campaign
    files did not change. Both proofs are still pending; no turn writes are enabled.

## Reclamation and disaster recovery

Do not generate artificial load to avoid reclamation. If Oracle stops the instance,
try starting it; free capacity may require waiting. If terminated, preserve/reuse
its boot/data volumes. Create only an eligible replacement in the same region and
availability domain as the retained data volume, within the aggregate quota. Attach
and mount that volume WITHOUT formatting. Restore packages/code/config from this
branch and your password manager. Update DuckDNS's IPv4 to the replacement IP.
The hostname and OAuth audience stay the same, and certificate state remains on disk.
Never delete old data to make room blindly; retained boots count against 200 GB.

If the entire data volume is lost, stop and restore only the existing staging Git
history and inspect accepted receipts. The unchanged gateway checkpoints accepted
work remotely; its storage-generation fence and this launcher's read-only restriction
prevent automatic turn resumption. Local-only unacknowledged drafts are not promised
as preserved bytes. Do not reset Git, delete leases or reroll. Original SIGKILL,
complete-disk-loss and partial-batch tests remain in the inherited suite.

Record volume/instance OCIDs, account home region, hostname and code SHA outside
Oracle, and keep credentials in your password manager. Git-accepted campaign history
and managed Auth0 survive loss of this VM independently. No Oracle volume alone
protects against an entire tenancy deletion. Optional manual backups must remain
within the five combined free backups; no automatic paid backup/replication policy.
Recheck the account and notices regularly; DNS activity does not guarantee retention.

## Verification and release boundary

Fresh logs record 73 passing unittest cases in seven suites, including four new
Oracle launcher guards and all 69 inherited adapter/gateway/recovery cases.
All 1,191 tracked files outside development and the adapter, lock, gateway,
HTTP service and diagnostic code are byte-identical to 09a3094.
Fresh test logs are committed with this proposal. The mount/write guards and core
regressions can run locally; ARM execution, Oracle account eligibility/capacity,
public DNS, ACME issuance, Auth0 tenant linking and both native-mobile proofs cannot
be certified without the owner's actual account/approved deployment. No OCI connection
was available here. A working free account and available A1 capacity are prerequisites,
not completed deliverables. No paid component is needed in this design, but a permanent
uptime guarantee or avoidance of the signup hold cannot be supplied for $0.

Sources checked: Oracle Always Free Resources and Free Tier FAQ; Oracle Managing
Account Upgrades; Oracle Arm-Based Compute (conflicting higher allowance); Oracle
VCN Pricing and Terminating an Instance; DuckDNS specification; Caddy installation
and Automatic HTTPS; Let's Encrypt challenge types; Auth0 pricing. Direct URLs:
https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
https://www.oracle.com/cloud/free/faq/
https://docs.oracle.com/en-us/iaas/Content/Billing/Tasks/changingpaymentmethod.htm
https://docs.oracle.com/en-us/iaas/Content/Compute/References/arm.htm
https://www.oracle.com/cloud/networking/virtual-cloud-network/pricing/
https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/terminatinginstance.htm
https://www.duckdns.org/spec.jsp
https://caddyserver.com/docs/automatic-https
https://auth0.com/pricing
