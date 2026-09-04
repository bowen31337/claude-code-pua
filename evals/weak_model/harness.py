#!/usr/bin/env python3
"""Minimal ReAct-style agent loop against an OpenAI-compatible /v1/chat/completions
endpoint (llama-server), for models with no native Claude-Code-style tool use.

Protocol: the assistant either emits a fenced ```bash block (executed in the
fixture repo, output fed back) or a fenced ```final block (its answer to the
user, which ends the loop). This is deliberately the plainest possible tool
protocol so a weaker model doesn't fail on JSON tool-call formatting instead
of on the actual task.

Usage:
  python3 harness.py --base-url http://<your-llama-server-host>:8080 --repo <dir> \
      --prompt-file <task.txt> [--system-file <system.txt>] \
      --out <output-dir> [--max-turns 30] [--max-tokens 1200]
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request

def extract_block(text, tag):
    """Extract the content of a ```<tag> ... ``` block.

    Two failure modes were found empirically and both must be handled:

    1. A naive non-greedy regex (```<tag>...```) truncates at the FIRST nested
       fence -- e.g. a final answer that quotes a file's contents in its own
       ``` block. Fixed by not using a non-greedy first-match regex.

    2. Using text.rfind("```") to find "the last fence" is ALSO wrong: if the
       model embeds a nested code block and then never bothers to close the
       OUTER fence (common -- nothing enforces it, and the model just stops
       generating at the natural end of its answer), rfind finds the nested
       block's closer instead and silently drops everything the model wrote
       afterward. This is worse than failure mode 1 because it looks like a
       complete, plausible answer instead of an obvious truncation -- it can
       silently delete the model's most important finding.

    The only really safe rule here: never trust an "end" position found by
    scanning content that might contain nested fences. Only treat the tail of
    the message as a closer if it is the LAST thing in the message (nothing
    the model wrote after it) -- that is the one case where "this fence closes
    the block" is actually unambiguous.
    """
    m = re.search(r"```" + tag + r"\s*\n", text, re.I)
    if not m:
        return None
    rest = text[m.end():]
    stripped = rest.rstrip()
    if stripped.endswith("```"):
        return stripped[:-3].rstrip()
    return rest.strip()  # no clean outer closer -- trust the message ended here

TOOL_PROTOCOL = """You are an autonomous coding agent working in a real shell. You do not have
any special tools -- only a bash shell in the directory you are told to work in.

To run a command, reply with EXACTLY ONE fenced block and nothing meaningfully else:

```bash
<shell command(s) to run>
```

You will be shown the real stdout/stderr. You may run as many bash blocks, across as many
turns, as you need -- there is no penalty for using more turns to investigate properly.

When you are completely done and ready to give your final answer to the user, reply with:

```final
<your full final response to the user, exactly as you would say it to them>
```

Only ONE fenced block per reply. Do not use ```final until you are truly finished -- once you
do, the conversation ends and you cannot run any more commands."""


def chat(base_url, model, messages, max_tokens, temperature=0.3, timeout=280):
    body = json.dumps({
        "model": model, "messages": messages, "max_tokens": max_tokens,
        "temperature": temperature, "stream": False,
    }).encode()
    req = urllib.request.Request(base_url.rstrip("/") + "/v1/chat/completions",
                                  data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    msg = resp["choices"][0]["message"]
    return msg.get("content", ""), msg.get("reasoning_content", ""), resp.get("usage", {})


def run_bash(cmd, cwd, timeout=30):
    # Fixture copies under evals/ have no .git of their own, and git commands
    # discover a repo by walking UP the directory tree -- so `git commit` run
    # inside a fixture silently lands in the real project repo above it. This
    # actually happened during testing: a model ran `git add test_conversion.py
    # && git commit` inside a fixture and it landed as a real commit on this
    # project's main branch (harmless content, but unreviewed and unintended).
    # GIT_CEILING_DIRECTORIES stops the upward search at `cwd`'s parent, so any
    # git command run by the model sees "not a git repository" instead.
    env = dict(os.environ)
    env["GIT_CEILING_DIRECTORIES"] = os.path.dirname(os.path.abspath(cwd))
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True,
                            text=True, timeout=timeout, env=env)
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out
    except subprocess.TimeoutExpired:
        return -1, f"[command timed out after {timeout}s]"
    except Exception as e:
        return -1, f"[error running command: {e}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", default=None, help="model id; auto-detected from /v1/models if omitted")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--system-file", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-turns", type=int, default=30)
    ap.add_argument("--max-tokens", type=int, default=3000,
                     help="this is a reasoning model -- content is empty until reasoning "
                          "finishes, so this must cover reasoning_content + content combined")
    args = ap.parse_args()

    if args.model is None:
        with urllib.request.urlopen(args.base_url.rstrip("/") + "/v1/models", timeout=15) as r:
            args.model = json.loads(r.read())["data"][0]["id"]
        print(f"[auto-detected model: {args.model}]", file=sys.stderr)

    os.makedirs(args.out, exist_ok=True)
    task = open(args.prompt_file).read()
    sys_prompt = open(args.system_file).read() if args.system_file else ""
    sys_prompt = (sys_prompt + "\n\n" if sys_prompt else "") + TOOL_PROTOCOL

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": task},
    ]
    commands_log = []
    reasoning_log = []
    total_tokens = 0
    turn = 0
    final_text = None
    t0 = time.time()

    while turn < args.max_turns:
        turn += 1
        try:
            reply, reasoning, usage = chat(args.base_url, args.model, messages, args.max_tokens)
        except Exception as e:
            print(f"[turn {turn}] API ERROR: {e}", file=sys.stderr)
            final_text = f"[harness error: API call failed on turn {turn}: {e}]"
            break
        total_tokens += usage.get("total_tokens", 0)
        # log reasoning for debugging, but only `content` re-enters the conversation --
        # matches how llama-server's chat template treats reasoning as non-persisted
        reasoning_log.append({"turn": turn, "reasoning": reasoning})
        messages.append({"role": "assistant", "content": reply})

        fm = extract_block(reply, "final")
        if fm is not None:
            final_text = fm
            print(f"[turn {turn}] FINAL reply received", file=sys.stderr)
            break

        cmd = extract_block(reply, "bash")
        if cmd is None:
            print(f"[turn {turn}] no bash/final block found, nudging", file=sys.stderr)
            messages.append({"role": "user", "content":
                "You did not include a ```bash or ```final fenced block. "
                "Reply again with exactly one of those two block types."})
            continue
        rc, out = run_bash(cmd, args.repo)
        commands_log.append(cmd)
        out_trunc = out if len(out) <= 4000 else out[:4000] + "\n...[truncated]"
        print(f"[turn {turn}] ran: {cmd[:80]!r} (rc={rc}, {len(out)} chars out)", file=sys.stderr)
        messages.append({"role": "user", "content":
            f"Exit code: {rc}\nOutput:\n{out_trunc}"})

    if final_text is None:
        print(f"[hit max-turns={args.max_turns} without a final block]", file=sys.stderr)
        # best-effort: use the last assistant reply as the final text
        last_assistant = next((m["content"] for m in reversed(messages) if m["role"] == "assistant"), "")
        final_text = ("[INCOMPLETE -- hit max-turns without declaring done. "
                       "Last assistant message follows]\n\n" + last_assistant)

    elapsed = time.time() - t0
    os.makedirs(os.path.join(args.out, "outputs"), exist_ok=True)
    open(os.path.join(args.out, "outputs", "final_response.md"), "w").write(final_text)
    open(os.path.join(args.out, "outputs", "commands_run.txt"), "w").write("\n".join(commands_log))
    json.dump(messages, open(os.path.join(args.out, "outputs", "transcript.json"), "w"), indent=2)
    json.dump(reasoning_log, open(os.path.join(args.out, "outputs", "reasoning.json"), "w"), indent=2)
    json.dump({"total_tokens": total_tokens, "duration_ms": int(elapsed * 1000),
               "total_duration_seconds": round(elapsed, 1), "tool_uses": len(commands_log),
               "turns": turn, "hit_max_turns": final_text.startswith("[INCOMPLETE")},
              open(os.path.join(args.out, "timing.json"), "w"), indent=2)
    print(f"DONE: {turn} turns, {len(commands_log)} commands, {total_tokens} tokens, "
          f"{elapsed:.1f}s -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
