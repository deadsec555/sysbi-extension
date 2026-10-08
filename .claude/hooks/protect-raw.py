#!/usr/bin/env python3
"""PreToolUse hook: nothing may modify or delete files in raw/ (original footage).

Reading raw/ is fine (ffmpeg -i raw/..., ffprobe, ls). Adding NEW footage is fine
(mkdir, cp -n / --no-clobber into raw/). Everything else that targets raw/ is blocked.
"""

import json
import re
import shlex
import sys

data = json.load(sys.stdin)
tool = data.get("tool_name", "")
inp = data.get("tool_input", {}) or {}


def in_raw(path: str) -> bool:
    return bool(re.search(r"(^|/)raw(/|$)", path or ""))


def block(why: str) -> None:
    print(f"Blocked: raw/ holds the original footage and must never be modified or deleted ({why}). "
          "Write results to transcripts/, shotlogs/, animations/, broll/, audio/ or output/ instead.", file=sys.stderr)
    sys.exit(2)


if tool in {"Edit", "Write", "NotebookEdit", "MultiEdit"}:
    if in_raw(inp.get("file_path", "")) or in_raw(inp.get("notebook_path", "")):
        block(f"{tool} on {inp.get('file_path') or inp.get('notebook_path')}")
    sys.exit(0)

if tool != "Bash":
    sys.exit(0)

cmd = inp.get("command", "")
if not re.search(r"(^|[\s'\"=/])raw(/|\s|$|['\"])", cmd):
    sys.exit(0)

# Split into simple commands and inspect each one that mentions raw/.
for part in re.split(r"&&|\|\||;|\||\n", cmd):
    if "raw" not in part:
        continue
    if re.search(r">>?\s*\S*\braw/", part):
        block("redirecting output into raw/")
    try:
        toks = shlex.split(part)
    except ValueError:
        toks = part.split()
    if not toks:
        continue
    # skip env assignments / sudo / time
    while toks and (re.match(r"^\w+=", toks[0]) or toks[0] in {"sudo", "time", "nice", "command"}):
        toks = toks[1:]
    if not toks:
        continue
    prog = toks[0].rsplit("/", 1)[-1]
    args = toks[1:]
    raw_args = [a for a in args if in_raw(a)]
    if not raw_args:
        continue
    if prog in {"rm", "rmdir", "unlink", "shred", "truncate", "chmod", "chown", "touch", "dd", "rsync", "ln"}:
        block(f"{prog} on raw/")
    if prog == "mv":
        block("mv touching raw/")
    if prog == "cp":
        dest = args[-1]
        if in_raw(dest) and not any(a in {"-n", "--no-clobber", "--update=none"} for a in args):
            block("cp into raw/ without -n (could overwrite footage)")
    if prog in {"sed", "perl"} and any(a.startswith("-i") or a == "--in-place" for a in args):
        block(f"{prog} in-place edit")
    if prog == "tee":
        block("tee into raw/")
    if prog == "find" and any(a in {"-delete", "-exec", "-execdir", "-ok"} for a in args):
        block("find -delete/-exec under raw/")
    if prog in {"ffmpeg", "sox", "magick", "convert", "exiftool", "mogrify"}:
        if prog == "exiftool" or prog == "mogrify":
            block(f"{prog} rewrites files in place")
        if in_raw(args[-1]):
            block(f"{prog} writing its output into raw/")
    if prog == "git" and any(a in {"rm", "mv", "checkout", "restore", "clean", "reset"} for a in args):
        block("git command that can change raw/")
    if prog in {"python", "python3", "node"} and "-c" in args:
        code = " ".join(args)
        if re.search(r"(unlink|remove|rmtree|rename|replace|write|open\([^)]*['\"][wa])", code):
            block("inline script that writes or deletes under raw/")
sys.exit(0)
