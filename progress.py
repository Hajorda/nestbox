"""Progress of a scrape run, written to progress.json so the control panel can show a bar, the stage and a time estimate.

Units are requests (a search page, a listing page, a Gemini call). The time estimate uses the measured speed of the
current stage once a few units are done, and default speeds before that, so it gets more accurate as the run goes on.
"""
import json, os, tempfile, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(HERE, "progress.json")
DEFAULT_SEC = {"search": 3.4, "read": 3.7, "ai": 5.0, "build": 1.0}     # typical seconds per unit
LABELS = {"search": "Searching listing sites", "read": "Reading listing pages", "ai": "Gemini reading descriptions", "build": "Ranking and building the page"}
ORDER = ("search", "read", "ai", "build")


class Progress:
    def __init__(self, plan):
        self.t0 = time.time()
        self.s = {k: {"total": plan.get(k, 0), "done": 0, "t0": None, "state": "pending"} for k in ORDER}
        self.cur, self.detail, self._last = None, "", 0.0
        self.lock = threading.RLock()                                      # ticks come from several threads (page readers and the Gemini worker)
        self.write(force=True)

    def stage(self, key, total=None, detail=""):
        if self.cur:
            c = self.s[self.cur]
            c["done"], c["state"] = c["total"] if c["total"] else c["done"], "done"   # an estimate that was too high just ends here
        self.cur = key
        c = self.s[key]
        c["state"], c["t0"] = "active", c["t0"] or time.time()             # keep the start time if this stage already began (it overlapped another one)
        if total is not None:
            c["total"] = total
        self.detail = detail
        self.write(force=True)

    def adjust_total(self, delta):
        if self.cur:
            self.s[self.cur]["total"] = max(self.s[self.cur]["done"], self.s[self.cur]["total"] + delta)

    def done(self, key=None):
        return self.s[key or self.cur]["done"] if (key or self.cur) else 0

    def tick(self, n=1, detail=None, stage=None):
        key = stage or self.cur
        if not key:
            return
        with self.lock:
            c = self.s[key]
            if c["state"] == "pending":
                c["state"], c["t0"] = "active", time.time()                # a stage that overlaps another one starts on its first tick
            c["done"] += n
            c["total"] = max(c["total"], c["done"])
            if detail:
                self.detail = detail
            self.write()

    def _rate(self, key):
        c = self.s[key]
        if c["t0"] and c["done"] >= 3:
            return max(0.3, (time.time() - c["t0"]) / c["done"])
        return DEFAULT_SEC[key]

    def eta(self):
        rem = {k: (0 if self.s[k]["state"] == "done" else max(0, self.s[k]["total"] - self.s[k]["done"]) * self._rate(k)) for k in ORDER}
        return int(rem["search"] + max(rem["read"], rem["ai"]) + rem["build"])     # reading and Gemini overlap: they cost the longer of the two

    def fraction(self):
        done = sum(min(c["done"], c["total"]) * DEFAULT_SEC[k] for k, c in self.s.items())
        whole = sum(c["total"] * DEFAULT_SEC[k] for k, c in self.s.items())
        return round(done / whole, 3) if whole else 0.0

    def write(self, force=False, running=True):
        now = time.time()
        if not force and now - self._last < 0.5:
            return
        with self.lock:
            self._write(now, running)

    def _write(self, now, running):
        self._last = now
        data = {"running": running, "stage": self.cur, "label": LABELS.get(self.cur, ""), "detail": self.detail, "overall": self.fraction(),
                "eta_seconds": self.eta() if running else 0, "started": self.t0, "updated": now,
                "stages": [{"key": k, "label": LABELS[k], "done": c["done"], "total": c["total"], "state": c["state"]} for k, c in self.s.items()]}
        fd, tmp = tempfile.mkstemp(dir=HERE)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp, FILE)

    def finish(self):
        for c in self.s.values():
            c["state"], c["done"] = "done", max(c["done"], c["total"])
        self.cur, self.detail = None, "finished"
        self.write(force=True, running=False)
