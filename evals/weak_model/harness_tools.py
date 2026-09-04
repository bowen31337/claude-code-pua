#!/usr/bin/env python3
"""Agent loop against an OpenAI-compatible /v1/chat/completions endpoint using
REAL function-calling (the `tools` parameter), instead of harness.py's fenced-block
convention.

Why this exists: the fenced-block harness asks the model to override its own
natively-trained tool-calling format. On repeated runs, some with-skill runs (whose
system prompt is much longer) drifted back to the model's native format mid-task,
producing unparseable garbage and burning out the turn budget -- 3 of 48 runs across
6 iterations, all on with-skill. This harness removes that confound by using the
model's native format directly: one `bash` tool, and the loop ends when the model
replies with no tool_calls (a plain final message), which is the standard shape for
tool-calling loops rather than an ad-hoc ```final convention.

Usage: same flags as harness.py.
"""
import argparse, json, os, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import run_bash  # reuses the GIT_CEILING_DIRECTORIES isolation fix

BASH_TOOL = [{
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Execute a shell command in the working directory and return its stdout/stderr.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "the shell command to run"}},
            "required": ["command"],
        },
    },
}]

SYSTEM_SUFFIX = ("\n\nYou have one tool available: `bash`, which runs a shell command in your "
                 "working directory and returns its output. Use it as many times as you need. "
                 "When you are completely finished and ready to give your final answer to the "
                 "user, reply with a normal text message (no tool call) containing your full "
                 "answer, exactly as you would say it to them.")


def chat(base_url, model, messages, max_tokens, temperature=0.3, timeout=280):
    body = json.dumps({
        "model": model, "messages": messages, "max_tokens": max_tokens,
        "temperature": temperature, "stream": False,
        "tools": BASH_TOOL, "tool_choice": "auto",
    }).encode()
    req = urllib.request.Request(base_url.rstrip("/") + "/v1/chat/completions",
                                  data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    return resp["choices"][0]["message"], resp.get("usage", {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", default=None)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--system-file", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-turns", type=int, default=25)
    ap.add_argument("--max-tokens", type=int, default=3000)
    args = ap.parse_args()

    if args.model is None:
        with urllib.request.urlopen(args.base_url.rstrip("/") + "/v1/models", timeout=15) as r:
            args.model = json.loads(r.read())["data"][0]["id"]
        print(f"[auto-detected model: {args.model}]", file=sys.stderr)

    os.makedirs(os.path.join(args.out, "outputs"), exist_ok=True)
    task = open(args.prompt_file).read()
    sys_prompt = open(args.system_file).read() if args.system_file else \
        "You are an autonomous coding agent."
    sys_prompt += SYSTEM_SUFFIX

    messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": task}]
    commands_log, reasoning_log = [], []
    total_tokens = 0
    turn = 0
    final_text = None
    t0 = time.time()

    while turn < args.max_turns:
        turn += 1
        try:
            msg, usage = chat(args.base_url, args.model, messages, args.max_tokens)
        except Exception as e:
            print(f"[turn {turn}] API ERROR: {e}", file=sys.stderr)
            final_text = f"[harness error: API call failed on turn {turn}: {e}]"
            break
        total_tokens += usage.get("total_tokens", 0)
        reasoning_log.append({"turn": turn, "reasoning": msg.get("reasoning_content", "")})

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            final_text = msg.get("content", "") or ""
            print(f"[turn {turn}] FINAL reply received (no tool call)", file=sys.stderr)
            break

        # Assistant message must be echoed back (with its tool_calls) before the
        # tool results, or the conversation is malformed for the next request.
        messages.append({"role": "assistant", "content": msg.get("content", ""),
                          "tool_calls": tool_calls})

        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name")
            try:
                cmd = json.loads(fn.get("arguments") or "{}").get("command", "")
            except json.JSONDecodeError:
                cmd = ""
            if name != "bash" or not cmd:
                out, rc = f"[unsupported tool call: {name!r} args={fn.get('arguments')!r}]", -1
            else:
                rc, out = run_bash(cmd, args.repo)
                commands_log.append(cmd)
            out_trunc = out if len(out) <= 4000 else out[:4000] + "\n...[truncated]"
            print(f"[turn {turn}] ran: {cmd[:80]!r} (rc={rc}, {len(out)} chars out)", file=sys.stderr)
            messages.append({"role": "tool", "tool_call_id": tc.get("id", ""),
                              "content": f"Exit code: {rc}\nOutput:\n{out_trunc}"})

    if final_text is None:
        print(f"[hit max-turns={args.max_turns} without a final message]", file=sys.stderr)
        last_content = next((m.get("content", "") for m in reversed(messages)
                              if m["role"] == "assistant" and m.get("content")), "")
        final_text = ("[INCOMPLETE -- hit max-turns without declaring done. "
                       "Last assistant text follows]\n\n" + last_content)

    elapsed = time.time() - t0
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
