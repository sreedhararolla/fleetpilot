#!/usr/bin/env python3
"""Duo hackathon referee: Claude Opus and GPT Sol build one project as a team.

The referee is neutral: it runs turns, enforces the clock and turn budget, commits
code on the agents' behalf, merges branches, logs everything, and calls the judge.
Agents communicate only through the shared board directory and git branches.
"""
import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAX_TURN_MINUTES = 20

CLAUDE_NET = [
    "pypi.org", "files.pythonhosted.org", "registry.npmjs.org", "github.com",
    "objects.githubusercontent.com", "raw.githubusercontent.com",
    "ercot.com", "www.ercot.com", "api.ercot.com", "apiexplorer.ercot.com",
    "mis.ercot.com", "api.eia.gov", "www.eia.gov", "api.weather.gov",
    "gridstatus.io", "api.gridstatus.io",
]

RULES = """# TEAM RULES (read every turn if unsure)
You are one of two AI engineers on a hackathon team: {a} and {b}. You are peers.
A neutral referee script runs turns; you never talk live. You communicate ONLY via:
- {board}/  shared board (you can write here):
  BRIEF.md (problem + rubric), PLAN.md, DECISIONS.md, tasks.json,
  pitches/, critiques/, reviews/, messages/
- git: each of you has your own branch + worktree. The referee commits your files after
  every turn and merges branches at sync points. Do NOT run git commit/merge yourself.

Every turn:
1. Read new messages (the referee lists them) and anything on the board you need.
2. Do the task for this turn. Stay inside your workspace and the board.
3. Before finishing, write board/messages/<turn>-<you>.md: what you did, what's next,
   what you need from your teammate (short, concrete).
tasks.json is a list of {{"id","title","owner","status":"todo|doing|done|blocked","notes"}}.
Only edit tasks you own (read-modify-write quickly). Disagree openly but briefly; record
decisions in DECISIONS.md. Optimize for a WORKING demo that wins, not for scope.
Never leave a server or watcher running in the foreground (streamlit, npm run dev, uvicorn...):
start it with `timeout 60 ...` or in the background, check it, then kill it before you finish.
"""


def now():
    return time.time()


def sh(cmd, cwd, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"{' '.join(cmd)} failed in {cwd}:\n{r.stdout}\n{r.stderr}")
    return r


class Agent:
    def __init__(self, name, model, run):
        self.name, self.model, self.run = name, model, run
        self.session = None
        self.turns = 0
        self.seen_msgs = set()
        self.last_text = ""
        self.tokens = {"in": 0, "out": 0}
        self.cost_usd = 0.0

    @property
    def wt(self):
        return self.run.dir / f"wt-{self.name}"

    def call(self, prompt, cwd, timeout):
        raise NotImplementedError


class ClaudeAgent(Agent):
    def call(self, prompt, cwd, timeout):
        settings = {"sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True,
                                "allowUnsandboxedCommands": False,
                                "network": {"allowedDomains": CLAUDE_NET}}}
        cmd = ["claude", "-p", "--model", self.model, "--output-format", "json",
               "--permission-mode", "acceptEdits", "--settings", json.dumps(settings),
               "--strict-mcp-config", "--allowedTools", "Bash", "WebSearch", "WebFetch",
               "--add-dir", str(self.run.board)]
        if self.session:
            cmd += ["--resume", self.session]
        else:
            self.session = str(uuid.uuid4())
            cmd += ["--session-id", self.session]
        r = subprocess.run(cmd, cwd=cwd, input=prompt, capture_output=True, text=True, timeout=timeout)
        if "Sandbox disabled" in r.stderr:
            raise RuntimeError("Claude sandbox is disabled; refusing to continue:\n" + r.stderr)
        try:
            d = json.loads(r.stdout)
        except json.JSONDecodeError:
            return r.stdout + r.stderr, {"error": r.stderr[-2000:]}
        u = d.get("usage", {})
        self.tokens["in"] += u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
        self.tokens["out"] += u.get("output_tokens", 0)
        self.cost_usd = d.get("total_cost_usd") or self.cost_usd  # cumulative over the resumed session
        return d.get("result", ""), d


class CodexAgent(Agent):
    def call(self, prompt, cwd, timeout):
        cfg = ['sandbox_mode="workspace-write"', 'approval_policy="never"', 'web_search="live"',
               "sandbox_workspace_write.network_access=true",
               "sandbox_workspace_write.exclude_slash_tmp=true",
               "sandbox_workspace_write.exclude_tmpdir_env_var=true",
               f'sandbox_workspace_write.writable_roots=["{self.run.board}"]']
        flags = ["-m", self.model, "--json", "--skip-git-repo-check"]
        for c in cfg:
            flags += ["-c", c]
        cmd = ["codex", "exec"] + (["resume", self.session] if self.session else []) + flags + ["-"]
        r = subprocess.run(cmd, cwd=cwd, input=prompt, capture_output=True, text=True, timeout=timeout)
        text, events = "", []
        for line in r.stdout.splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            events.append(e)
            if e.get("type") == "thread.started":
                self.session = e["thread_id"]
            elif e.get("type") == "item.completed" and e["item"].get("type") == "agent_message":
                text = e["item"]["text"]
            elif e.get("type") == "turn.completed":
                u = e.get("usage", {})  # cumulative over the resumed thread
                self.tokens["in"] = u.get("input_tokens", 0)
                self.tokens["out"] = u.get("output_tokens", 0)
        if not events:
            return r.stderr[-2000:], {"error": r.stderr[-2000:]}
        return text, events


class Run:
    def __init__(self, args):
        self.args = args
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.dir = (ROOT / "runs" / stamp).resolve()
        self.board, self.repo, self.logs = self.dir / "board", self.dir / "repo", self.dir / "logs"
        self.start = now()
        self.deadline = self.start + args.hours * 3600
        self.turn_no = 0
        self.lock = threading.Lock()
        self.opus = ClaudeAgent("opus", args.claude_model, self)
        self.sol = CodexAgent("sol", args.gpt_model, self)
        self.agents = [self.opus, self.sol]

    # ---------- setup ----------
    def setup(self):
        for d in [self.board / "pitches", self.board / "critiques", self.board / "reviews",
                  self.board / "messages", self.logs / "raw", self.repo]:
            d.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.args.brief, self.board / "BRIEF.md")
        (self.board / "RULES.md").write_text(RULES.format(a="opus", b="sol", board=self.board))
        (self.board / "tasks.json").write_text("[]\n")
        (self.board / "DECISIONS.md").write_text("# Decisions\n")
        sh(["git", "init", "-q", "-b", "main"], self.board)
        self.commit(self.board, "referee", "board initialized")
        sh(["git", "init", "-q", "-b", "main"], self.repo)
        (self.repo / "README.md").write_text("# Hackathon project\n")
        (self.repo / ".gitignore").write_text("__pycache__/\n*.pyc\n.venv/\nnode_modules/\n.pytest_cache/\n")
        self.commit(self.repo, "referee", "init")
        for a in self.agents:
            sh(["git", "worktree", "add", "-q", "-b", a.name, str(a.wt)], self.repo)
        self.log(f"run dir {self.dir}")

    # ---------- helpers ----------
    def minutes_left(self):
        return max(0, (self.deadline - now()) / 60)

    def log(self, msg):
        line = f"[{dt.datetime.now():%H:%M:%S} | {self.minutes_left():5.1f}m left] {msg}"
        print(line, flush=True)
        with self.lock, open(self.logs / "referee.log", "a") as f:
            f.write(line + "\n")

    def commit(self, cwd, who, msg):
        sh(["git", "add", "-A"], cwd)
        if sh(["git", "diff", "--cached", "--quiet"], cwd, check=False).returncode == 0:
            return False
        sh(["git", "-c", f"user.name={who}", "-c", f"user.email={who}@duo.local",
            "commit", "-q", "-m", msg], cwd)
        return True

    def new_messages(self, agent):
        msgs = sorted(p.name for p in (self.board / "messages").glob("*.md"))
        fresh = [m for m in msgs if m not in agent.seen_msgs and not m.endswith(f"-{agent.name}.md")]
        agent.seen_msgs.update(msgs)
        return fresh

    def turn(self, agent, phase, task, cwd=None, extra_minutes=None):
        cwd = cwd or agent.wt
        other = self.sol if agent is self.opus else self.opus
        with self.lock:
            self.turn_no += 1
            n = self.turn_no
        agent.turns += 1
        budget = min(MAX_TURN_MINUTES, extra_minutes or MAX_TURN_MINUTES, self.minutes_left())
        fresh = self.new_messages(agent)
        header = RULES.format(a="opus", b="sol", board=self.board) + "\n" if agent.turns == 1 else ""
        prompt = f"""{header}[REFEREE] Turn #{n:03d} for {agent.name.upper()} (your turn {agent.turns}/{self.args.max_turns}).
Phase: {phase}. Time left in hackathon: {self.minutes_left():.0f} min. This turn: aim to finish in ~{budget:.0f} min.
Teammate: {other.name} (a different AI model). Shared board: {self.board}
Your working directory for this turn: {cwd}
New messages from teammate/referee: {', '.join(fresh) or 'none'} (in {self.board}/messages/)

TASK:
{task}

Finish by writing {self.board}/messages/{n:03d}-{agent.name}.md.
"""
        self.log(f"turn {n:03d} {agent.name} [{phase}] start")
        t0 = now()
        try:
            text, raw = agent.call(prompt, cwd, timeout=budget * 60 + 120)
        except subprocess.TimeoutExpired:
            text, raw = "(turn timed out)", {"error": "timeout"}
        dur = now() - t0
        (self.logs / "raw" / f"{n:03d}-{agent.name}.json").write_text(json.dumps(
            {"prompt": prompt, "result": text, "raw": raw}, indent=1, default=str))
        if cwd != self.board:
            self.commit(cwd, agent.name, f"{agent.name} turn {n:03d} ({phase})")
        with self.lock:
            self.commit(self.board, agent.name, f"{agent.name} turn {n:03d} board")
            rec = {"turn": n, "agent": agent.name, "phase": phase, "seconds": round(dur),
                   "tokens": dict(agent.tokens), "cost_usd": round(agent.cost_usd, 3),
                   "summary": text[:600]}
            with open(self.logs / "turns.jsonl", "a") as f:
                f.write(json.dumps(rec) + "\n")
        agent.last_text = text
        self.log(f"turn {n:03d} {agent.name} done in {dur/60:.1f}m: {text[:160]!r}")
        return text

    def both(self, fn):
        errors = []

        def wrap(a):
            try:
                fn(a)
            except Exception as e:
                errors.append(e)
        ts = [threading.Thread(target=wrap, args=(a,)) for a in self.agents]
        [t.start() for t in ts]
        [t.join() for t in ts]
        if errors:
            raise errors[0]

    def merge_into(self, cwd, branch):
        """Merge branch into the worktree at cwd; leave conflict markers for the agent to fix."""
        r = sh(["git", "-c", "user.name=referee", "-c", "user.email=referee@duo.local",
                "merge", "--no-edit", branch], cwd, check=False)
        if r.returncode == 0:
            return []
        files = sh(["git", "diff", "--name-only", "--diff-filter=U"], cwd, check=False).stdout.split()
        if not files:
            sh(["git", "merge", "--abort"], cwd, check=False)
        return files

    def resolve_prompt(self, conflicts, branch):
        return (f"The referee merged `{branch}` into your workspace and git reports conflicts in: "
                f"{', '.join(conflicts)}. Resolve every conflict marker so both teammates' work is kept "
                "and the project runs. Do not run git commands that commit; the referee commits.\n")

    def has_turns(self, a, reserve):
        return a.turns < self.args.max_turns - reserve

    # ---------- phases ----------
    def play(self):
        A = self.args
        driver = self.opus if A.first_driver == "opus" else self.sol
        nav = self.sol if driver is self.opus else self.opus
        b = self.board

        self.both(lambda a: self.turn(a, "1-PITCH", f"""Read {b}/BRIEF.md. Research as needed (web search is allowed:
the event, the host, the tracks, the data available). WITHOUT reading your teammate's pitch, write
{b}/pitches/{a.name}.md: which track and why it maximizes prize odds, the project idea, who it's
for, the demo moment, the architecture, the data sources (verify they are reachable), what is
buildable in {self.minutes_left()*0.6:.0f} build-minutes by two engineers, the main risks, and 1-2 backup ideas.""", cwd=b, extra_minutes=15))

        self.both(lambda a: self.turn(a, "2-CRITIQUE", f"""Read both pitches in {b}/pitches/. Write
{b}/critiques/{a.name}-on-{'sol' if a is self.opus else 'opus'}.md: an honest critique of your teammate's pitch
(prize odds, feasibility in the time box, demo risk, relevance to the host), then a short, fair
comparison of both pitches and which direction (or hybrid) you now believe wins. Change your mind if warranted.""", cwd=b, extra_minutes=10))

        self.turn(driver, "3-MERGE (driver)", f"""You are this phase's driver. Read the pitches and critiques. Write
{b}/PLAN.md: the chosen track, the project, the demo script outline, the architecture, the repo layout,
the interfaces between components (so you two can build in parallel without collisions), and a definition
of done. Fill {b}/tasks.json with 6-14 tasks, each with an owner (opus or sol), split so you both work in
parallel on separate files/dirs. Log key choices in {b}/DECISIONS.md.""", cwd=b, extra_minutes=15)
        self.turn(nav, "3-MERGE (navigator)", f"""Your teammate drafted {b}/PLAN.md and {b}/tasks.json. Review them critically.
Edit them directly where you're confident it improves prize odds or feasibility; put any objection you
couldn't resolve under '## Open objections' in {b}/DECISIONS.md with a proposed alternative.""", cwd=b, extra_minutes=10)
        self.turn(driver, "3-MERGE (final)", f"""Finalize the plan. Address each open objection in {b}/DECISIONS.md:
accept it or explain why not in one line. After this turn the plan is locked (small adjustments are fine later).
Make sure every task has one owner and interfaces are explicit.""", cwd=b, extra_minutes=8)

        build_end = self.deadline - A.post_build_minutes * 60
        rnd = 0
        while now() < build_end and all(self.has_turns(a, 4) for a in self.agents):
            rnd += 1
            if rnd > 1 and (rnd - 1) % A.sync_every == 0:
                self.log(f"sync point before round {rnd}")
                for a in self.agents:
                    other = "sol" if a is self.opus else "opus"
                    self.commit(a.wt, a.name, "pre-sync")
                    a.pending_conflicts = self.merge_into(a.wt, other)
            mins = min(MAX_TURN_MINUTES, (build_end - now()) / 60)

            def build_turn(a):
                conflicts = getattr(a, "pending_conflicts", [])
                a.pending_conflicts = []
                pre = self.resolve_prompt(conflicts, "sol" if a is self.opus else "opus") if conflicts else ""
                self.turn(a, f"4-BUILD r{rnd}", pre + f"""Build your tasks from {b}/tasks.json per {b}/PLAN.md in
your workspace {a.wt}. Pick the highest-value unfinished task you own (or help unblock your teammate).
Write tests for core logic and run them. Update your task statuses. Build-phase time left:
{(build_end-now())/60:.0f} min. Your teammate's latest code is on git branch
`{'sol' if a is self.opus else 'opus'}` (read with `git show <branch>:<path>`); it is merged into yours every
{A.sync_every} rounds.
If all your tasks are done, don't idle: pick the improvement that most raises the rubric score (demo impact,
depth, polish), add it as a task you own, and build it. End your final reply with the line
`BUILD_STATUS: DONE` only if you believe more build work would not improve the odds of winning;
otherwise end with `BUILD_STATUS: CONTINUE`. The build ends early when both of you say DONE.""", extra_minutes=mins)
            self.both(build_turn)
            if all(a.last_text.rstrip().endswith("BUILD_STATUS: DONE") for a in self.agents):
                self.log("both agents declared the build done; moving to review early")
                break

        self.log("build phase over; cross-review")
        for a in self.agents:
            self.commit(a.wt, a.name, "pre-review")
            a.pending_conflicts = self.merge_into(a.wt, "sol" if a is self.opus else "opus")
        self.both(lambda a: self.turn(a, "5-REVIEW", (self.resolve_prompt(a.pending_conflicts, "teammate") if a.pending_conflicts else "") +
            f"""Both branches are now merged into your workspace. Review the code your TEAMMATE wrote
(`git log --author={'sol' if a is self.opus else 'opus'} -p` helps). Write {b}/reviews/{a.name}.md: bugs, broken
demo paths, missing tests, rubric gaps, ranked by severity. Fix any merge breakage you find right now and run the tests.""", extra_minutes=12))
        self.both(lambda a: self.turn(a, "5-FIX", f"""Read {b}/reviews/ (your teammate's review of YOUR code).
Fix the valid findings in your code (push back in your message if you disagree). Run the tests.""", extra_minutes=12))

        self.log("integration on main")
        conflicts = []
        for a in self.agents:
            self.commit(a.wt, a.name, "pre-integration")
            if not conflicts:  # can't start a second merge while the first is unresolved
                conflicts += self.merge_into(self.repo, a.name)
        self.turn(nav, "6-INTEGRATE (driver)", (self.resolve_prompt(conflicts, "opus+sol") if conflicts else "") +
            f"""You drive integration. {self.repo} (branch main) now holds both branches merged. Make it run
end-to-end from README.md with one command, make all tests pass, and write README.md, DEMO.md and
PITCH.md per {b}/BRIEF.md. Actually run the demo path and fix what breaks.""", cwd=self.repo, extra_minutes=15)
        self.turn(driver, "6-INTEGRATE (verify)", f"""Final check before judging. In {self.repo}: follow README.md exactly
from a clean state, run the tests and walk the DEMO.md script. Fix anything broken. Tighten PITCH.md and
DEMO.md so they score well against the rubric in {b}/BRIEF.md. No new features.""", cwd=self.repo, extra_minutes=12)

    # ---------- judge ----------
    def judge(self):
        jdir = self.dir / "judge"
        sh(["git", "clone", "-q", str(self.repo), str(jdir)], self.dir)
        schema = {"type": "object", "additionalProperties": False,
                  "required": ["track", "criteria", "overall", "summary", "strengths", "weaknesses", "demo_ran"],
                  "properties": {
                      "track": {"type": "string"},
                      "criteria": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                   "required": ["name", "score", "justification"],
                                   "properties": {"name": {"type": "string"}, "score": {"type": "number"},
                                                  "justification": {"type": "string"}}}},
                      "overall": {"type": "number"}, "summary": {"type": "string"},
                      "strengths": {"type": "array", "items": {"type": "string"}},
                      "weaknesses": {"type": "array", "items": {"type": "string"}},
                      "demo_ran": {"type": "boolean"}}}
        (self.dir / "judge_schema.json").write_text(json.dumps(schema))
        brief = (self.board / "BRIEF.md").read_text()
        prompt = f"""You are the impartial judge of a hackathon submission in {jdir}. The brief and rubric:

{brief}

Evaluate the submission as a demanding hackathon judge from the host company would. Actually install and
run it following README.md, run the tests, and walk DEMO.md. Never leave a server running in the
foreground: use `timeout` or background it and kill it afterwards. Score each rubric criterion 0-10 with a
justification grounded in what you observed. 'overall' is the mean. Be strict; don't reward claims you couldn't verify."""
        cfg = ['sandbox_mode="workspace-write"', 'approval_policy="never"',
               "sandbox_workspace_write.network_access=true"]
        cmd = ["codex", "exec", "-m", self.args.judge_model, "--skip-git-repo-check",
               "--output-schema", str(self.dir / "judge_schema.json"), "-o", str(self.dir / "JUDGE.json")]
        for c in cfg:
            cmd += ["-c", c]
        self.log(f"judging with {self.args.judge_model}")
        r = subprocess.run(cmd + ["-"], cwd=jdir, input=prompt, capture_output=True, text=True, timeout=45 * 60)
        (self.logs / "judge_stdout.txt").write_text(r.stdout + "\n" + r.stderr)
        self.log("judge done: " + (self.dir / "JUDGE.json").read_text()[:400] if (self.dir / "JUDGE.json").exists() else "judge failed")

    def summary(self):
        s = {"run_dir": str(self.dir), "minutes": round((now() - self.start) / 60, 1),
             "agents": {a.name: {"model": a.model, "turns": a.turns, "tokens": a.tokens,
                                 "cost_usd": round(a.cost_usd, 3)} for a in self.agents}}
        (self.dir / "SUMMARY.json").write_text(json.dumps(s, indent=2))
        self.log("summary: " + json.dumps(s))


def preflight():
    missing = [t for t in ["claude", "codex", "git", "bwrap", "socat"] if not shutil.which(t)]
    if missing:
        sys.exit(f"missing tools: {missing}. Claude's sandbox needs bwrap+socat: sudo apt install -y bubblewrap socat")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--brief", required=True, type=Path)
    p.add_argument("--hours", type=float, default=3.0)
    p.add_argument("--max-turns", type=int, default=40, help="per agent")
    p.add_argument("--claude-model", default="claude-opus-5-5")
    p.add_argument("--gpt-model", default="gpt-5.6-sol")
    p.add_argument("--judge-model", default="gpt-6-astra")
    p.add_argument("--first-driver", choices=["opus", "sol"], default="opus",
                   help="drives planning; the other drives integration")
    p.add_argument("--sync-every", type=int, default=3, help="build rounds between branch merges")
    p.add_argument("--post-build-minutes", type=float, default=55)
    p.add_argument("--no-judge", action="store_true")
    args = p.parse_args()
    preflight()
    run = Run(args)
    run.setup()
    try:
        run.play()
    finally:
        run.summary()
    if not args.no_judge:
        run.judge()


if __name__ == "__main__":
    main()
