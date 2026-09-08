"""Bind a readable $A-$B identity to every agent herdr detects.

The agent name dies with the agent; the pane label survives. So the pane label is the
durable identity, and the name is rebound from it whenever an agent reappears in the pane.

Three rules keep this from damaging state it does not own:
  - An existing agent name wins. `herdr agent start <name>` and role workflows pick names
    on purpose; overwriting one breaks the lookups that depend on it.
  - An existing pane label wins. Panes labelled by role ("Reviewer") keep that role.
  - A minted name is persisted as the label only after `herdr agent rename` accepted it,
    so a lost race never leaves a pane holding a name another agent owns.

Runs three ways, all the same code: on `pane.agent_detected` (one pane, from the event),
and from the startup hook or the `name-all` action (every agent that has no name).
"""
import json, os, random, re, subprocess, time

HERDR = os.environ.get("HERDR_BIN_PATH", "herdr")

# herdr's own agent-name rule; a label outside it can never become an agent name.
AGENT_NAME_RE = re.compile(r"[a-z][a-z0-9_-]{0,31}")
# ponytail: word lists inline. Move to $HERDR_PLUGIN_CONFIG_DIR/words.json when someone
# actually wants a different register without editing a managed checkout.
# Each theme is a (left, right) pair; names are drawn from the union, so adding a theme
# widens the pool instead of crowding an existing one.
THEMES = [
    ("white black orange amber blue coral green slate violet crimson teal olive indigo rust".split(),
     "fox cow cat otter heron lynx crane badger marten shrike ibis viper quokka tapir".split()),
    ("crispy salty spicy smoky sweet tangy chewy hearty zesty toasted savory buttery frosty crunchy".split(),
     "toast miso ramen bagel waffle taco gnocchi kimchi pretzel scone tofu mango pesto brioche".split()),
]


def herdr(*args):
    """Returns (result, error_code). error_code is '' on success."""
    try:
        out = subprocess.run([HERDR, *args], capture_output=True, text=True, timeout=3)
        payload = json.loads(out.stdout or out.stderr or "{}")
    except Exception:
        return {}, "unavailable"
    if payload.get("error"):
        return {}, payload["error"].get("code") or "unknown"
    return payload.get("result") or {}, ""


def occupant(pane):
    """The pane's agent, once herdr has classified it. Empty when nothing occupies it."""
    for _ in range(5):
        res, err = herdr("agent", "get", pane)
        if not err:
            return res.get("agent") or {}
        if err != "agent_not_found":
            return {}
        time.sleep(0.2)
    return {}


def claim(pane, name):
    for _ in range(5):
        _, err = herdr("agent", "rename", pane, name)
        if not err:
            return True
        if err == "agent_name_taken":
            return False
        time.sleep(0.2)
    return False


def mint(pane):
    for _ in range(3):
        used = {a.get("name") for a in herdr("agent", "list")[0].get("agents", [])}
        used |= {p.get("label") for p in herdr("pane", "list")[0].get("panes", [])}
        pool = [n for left, right in THEMES for a in left for b in right
                if (n := f"{a}-{b}") not in used]
        if not pool:
            return ""
        candidate = random.choice(pool)
        if claim(pane, candidate):  # won the name; only now safe to persist as the label
            herdr("pane", "rename", pane, candidate)
            return candidate
    return ""


def name_pane(pane):
    agent = occupant(pane)
    if not agent:
        return
    label = (herdr("pane", "get", pane)[0].get("pane") or {}).get("label") or ""

    existing = agent.get("name") or ""
    if existing:
        if not label:
            herdr("pane", "rename", pane, existing)
            print(f"{pane}: labelled {existing}")
        return

    if label:
        if AGENT_NAME_RE.fullmatch(label) and claim(pane, label):
            print(f"{pane}: rebound {label}")
        return

    if name := mint(pane):
        print(f"{pane}: named {name}")


# `pane.agent_detected` carries the pane under `data`; every other entrypoint sweeps.
event = json.loads(os.environ.get("HERDR_PLUGIN_EVENT_JSON") or "{}")
pane_id = (event.get("data") or {}).get("pane_id")
panes = [pane_id] if pane_id else [
    a["pane_id"] for a in herdr("agent", "list")[0].get("agents", []) if not a.get("name")
]

for pane in panes:
    name_pane(pane)
