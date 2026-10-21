"""First run: make sure config.json exists (copied from config.example.json) and tell the pages whether the setup wizard still has to be done."""
import json, os, shutil, tempfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
EXAMPLE = os.path.join(HERE, "config.example.json")
PLACEHOLDER_NAMES = {"", "Your Name"}


def ensure_config():
    """A fresh download has only config.example.json: copy it, so every part of the program finds a config."""
    if not os.path.exists(CONFIG) and os.path.exists(EXAMPLE):
        shutil.copyfile(EXAMPLE, CONFIG)
    return CONFIG


def load():
    ensure_config()
    with open(CONFIG) as f:
        return json.load(f)


def needs_setup(cfg):
    """True until the wizard was finished, unless the details were filled in by hand (an existing installation)."""
    if cfg.get("setup_done"):
        return False
    return (cfg.get("profile", {}).get("signature") or "").strip() in PLACEHOLDER_NAMES


def _write(cfg):
    fd, tmp = tempfile.mkstemp(dir=HERE)
    with os.fdopen(fd, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG)


def apply_setup(body):
    """Validate the wizard's answers and save them. Returns (error, None) or (None, cfg)."""
    cfg = load()
    p = cfg.setdefault("profile", {})
    try:
        name = str(body["name"]).strip()[:60]
        second = str(body.get("second_name") or "").strip()[:60]
        phone, email = str(body.get("phone") or "").strip()[:30], str(body.get("email") or "").strip()[:80]
        budget = int(body["budget"])
        mi, mo = str(body["move_in"]), str(body["move_out"])
        if not name:
            return "please enter your name", None
        if not 300 <= budget <= 5000:
            return "the budget must be between 300 and 5000 euros per month", None
        if date.fromisoformat(mo) <= date.fromisoformat(mi):
            return "the move-out date must be after the move-in date", None
        areas = body.get("areas") or []
        if not isinstance(areas, list) or not areas or any(a not in cfg.get("areas", {}) for a in areas):
            return "pick at least one area", None
    except (KeyError, TypeError, ValueError):
        return "some answers are missing or not valid", None
    p.update(signature=name, names=(name + (" and " + second if second else "")), second_name=second, phone=phone, email=email, move_in=mi, move_out=mo)
    if body.get("workplace"):
        p["workplace"] = str(body["workplace"]).strip()[:60]
    if body.get("internship_end"):
        date.fromisoformat(str(body["internship_end"]))
        p["internship_end"] = str(body["internship_end"])
    cfg["budget"] = budget
    cfg["enabled_areas"] = list(dict.fromkeys(areas))
    cfg["setup_done"] = True
    _write(cfg)
    return None, cfg
