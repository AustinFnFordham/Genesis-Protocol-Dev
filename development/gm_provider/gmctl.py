#!/usr/bin/env python3
"""Command-line face of the GM gateway, for agent-session providers and operators.

An agent session (for example the Claude cloud worker) is a GM provider like any other: it
claims the action routed to it, reads the GM context, and sends its moves through the same
validators. It uses this tool instead of an API key.

  gmctl.py -c DIR -i ID -s STORE state | providers | routing | recovery
  gmctl.py ... select PROVIDER                    choose the GM for new actions
  gmctl.py ... submit ACTION.json | status ACTION_ID | reroute ACTION_ID PROVIDER
  gmctl.py ... declare ACTION_ID PROVIDER "free text"   build a declaration on the current revision and submit it
  (every command accepts --shared DIR in place of -c -i -s)
  gmctl.py ... claim PROVIDER --run RUN --model M --session S    take the lease and the routed action
  gmctl.py ... context|publish|release PROVIDER --run RUN [--out FILE]
  gmctl.py ... review|tables|roll|commit PROVIDER --run RUN FILE.json
  gmctl.py ... run PROVIDER                       let a model-API provider play the whole turn

Exit codes: 0 done, 3 refused (the JSON says why), 2 usage.
"""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gateway import Gateway, Refused   # noqa: E402
import providers as provider_module    # noqa: E402
from runner import run_turn            # noqa: E402
from store import SqliteStore          # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-c", "--campaign", type=Path)
    parser.add_argument("-i", "--id")
    parser.add_argument("-s", "--store", type=Path)
    parser.add_argument("--shared", type=Path, help="a shared staging environment directory in this git clone (replaces -c -i -s)")
    parser.add_argument("command")
    parser.add_argument("args", nargs="*")
    parser.add_argument("--run")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--model", help="claim: the model this session says it is (attestation, recorded with the turn)")
    parser.add_argument("--session", help="claim: a session reference (URL or id) for the record")
    a = parser.parse_intermixed_args(argv)
    if a.shared:
        import staging
        gateway = staging.open_shared(a.shared)
    elif a.campaign and a.id and a.store:
        gateway = Gateway(a.campaign, a.id, SqliteStore(a.store))
    else:
        parser.exit(2, "give --shared DIR, or -c -i -s\n")
    load = lambda index: json.loads(Path(a.args[index]).read_text(encoding="utf-8"))
    try:
        c = a.command
        if c == "state":
            out = gateway.public_state()
        elif c == "providers":
            out = provider_module.matrix(provider_module.registry())
        elif c == "routing":
            out = gateway.routing()
        elif c == "recovery":
            out = gateway.recovery()
        elif c == "select":
            out = gateway.select_provider(a.args[0], by="operator")
        elif c == "submit":
            out = gateway.submit(load(0))
        elif c == "declare":       # declare ACTION_ID PROVIDER "free text": build against the current revision and submit
            import staging
            out = gateway.submit(staging.declare(gateway, a.args[0], text=a.args[2], provider=a.args[1]))
        elif c == "status":
            out = gateway.action_status(a.args[0])
        elif c == "reroute":
            out = gateway.reroute(a.args[0], a.args[1], by="operator")
        elif c == "run":
            registry = provider_module.registry()
            if a.args[0] not in registry:
                parser.exit(2, f"no model-API provider named {a.args[0]}\n")
            out = run_turn(gateway, registry[a.args[0]], run=a.run)
        elif c in ("claim", "context", "publish", "release", "review", "tables", "roll", "commit"):
            if not a.run:
                parser.exit(2, "--run is required\n")
            provider = a.args[0]
            out = {"claim": lambda: gateway.claim(provider, a.run, {"kind": "agent-session", "model": a.model, "session": a.session, "mock": False}), "context": lambda: gateway.context(provider, a.run),
                   "publish": lambda: gateway.publish(provider, a.run), "release": lambda: gateway.release(provider, a.run, "released by gmctl"),
                   "review": lambda: gateway.review(provider, a.run, load(1)), "tables": lambda: gateway.fix_tables(provider, a.run, load(1)),
                   "roll": lambda: gateway.roll(provider, a.run, load(1)), "commit": lambda: gateway.commit(provider, a.run, load(1))}[c]()
        else:
            parser.exit(2, f"unknown command {c}\n")
    except Refused as refusal:
        print(json.dumps(refusal.as_dict(), indent=1, ensure_ascii=False))
        return 3
    text = json.dumps(out, indent=1, ensure_ascii=False)
    if a.out:
        a.out.write_text(text, encoding="utf-8")
        print(json.dumps({"written": str(a.out), "bytes": len(text)}))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
