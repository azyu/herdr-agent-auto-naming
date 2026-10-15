"""Bind a readable $A-$B identity to every agent herdr detects.

The agent name dies with the agent; the pane label survives. So the pane label is the
durable identity, and the name is rebound from it whenever an agent reappears in the pane.

Three rules keep this from damaging state it does not own:
  - An existing agent name wins. `herdr agent start <name>` and role workflows pick names
    on purpose; overwriting one breaks the lookups that depend on it.
  - An existing pane label wins. Panes labelled by role ("Reviewer") keep that role.
  - A minted name is persisted as the label only after `herdr agent rename` accepted it,
    so a lost race never leaves a pane holding a name another agent owns.

Runs three ways, all the same code: on a pane event (one pane, from the event), and
from the startup hook or the `name-all` action (every agent that has no name). Both
`pane.agent_detected` and `pane.agent_status_changed` are subscribed: a session replaced
in place by `/clear` or `/new` drops the name without a detection event, so the status
change that follows it is the only event left to rebind from.
"""
import json, os, random, re, subprocess, sys, time

HERDR = os.environ.get("HERDR_BIN_PATH", "herdr")

# herdr's own agent-name rule; a label outside it can never become an agent name.
AGENT_NAME_RE = re.compile(r"[a-z][a-z0-9_-]{0,31}")
CONFIG_DIR = os.environ.get("HERDR_PLUGIN_CONFIG_DIR", "")
# The built-in "default" theme. Each theme is a (left, right) pair; names are drawn from
# the union of the selected themes, so adding one widens the pool instead of crowding
# an existing one. Other themes live in the user's config dir, never in this checkout.
THEMES = [
    ("white black orange amber blue coral green slate violet crimson teal olive indigo rust".split(),
     "fox cow cat otter heron lynx crane badger marten shrike ibis viper quokka tapir".split()),
    ("crispy salty spicy smoky sweet tangy chewy hearty zesty toasted savory buttery frosty crunchy".split(),
     "toast miso ramen bagel waffle taco gnocchi kimchi pretzel scone tofu mango pesto brioche".split()),
]


def load_themes():
    """Themes named in $HERDR_PLUGIN_CONFIG_DIR/config.json, e.g. {"themes": ["bishoujo"]}.

    "default" is the built-in THEMES; any other name is read from themes/<name>.json in the
    same dir as {"left": [...], "right": [...]}. No config means default. A broken config or
    theme is reported on stderr (the plugin log) and skipped rather than stopping naming.
    """
    if not CONFIG_DIR:
        return THEMES
    try:
        with open(os.path.join(CONFIG_DIR, "config.json"), encoding="utf-8") as f:
            names = json.load(f)["themes"]
        if not isinstance(names, list) or any(
            not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", name)
            for name in names
        ):
            raise ValueError("themes must be a list of names using letters, digits, '_' or '-'")
    except FileNotFoundError:
        return THEMES
    except Exception as e:
        print(f"config.json: {e!r}; using default", file=sys.stderr)
        return THEMES
    themes = []
    for name in names:
        if name == "default":
            themes += THEMES
            continue
        try:
            with open(os.path.join(CONFIG_DIR, "themes", f"{name}.json"), encoding="utf-8") as f:
                theme = json.load(f)
            left, right = theme["left"], theme["right"]
            if any(not isinstance(words, list) or any(not isinstance(word, str) for word in words)
                   for words in (left, right)):
                raise ValueError("left and right must be lists of strings")
            themes.append((left, right))
        except Exception as e:
            print(f"theme {name}: {e!r}; skipped", file=sys.stderr)
    return themes or THEMES


def herdr(*args):
    """Returns (result, error_code). error_code is '' on success."""
    try:
        out = subprocess.run(
            [HERDR, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=3,
        )
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
    themes = load_themes()
    for _ in range(3):
        used = {a.get("name") for a in herdr("agent", "list")[0].get("agents", [])}
        used |= {p.get("label") for p in herdr("pane", "list")[0].get("panes", [])}
        # User themes can hold words herdr would refuse; such a name could never be claimed.
        pool = [n for left, right in themes for a in left for b in right
                if (n := f"{a}-{b}") not in used and AGENT_NAME_RE.fullmatch(n)]
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
