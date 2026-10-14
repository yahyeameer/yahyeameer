"""Tic-tac-toe played through GitHub issues.

A visitor clicks an empty square in the README, which opens an issue titled
"ttt|move|<0-8>" (or "ttt|new"). The workflow runs this script with the issue
title and author, then commits the updated README and state file.
"""
import json
import os
import random
import re
import sys

REPO = os.environ.get("GITHUB_REPOSITORY", "yahyeameer/yahyeameer")
STATE = "game/ttt.json"
README = "README.md"
START, END = "<!-- TTT:START -->", "<!-- TTT:END -->"
LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
# The bot plays a random move this often, so humans can actually win.
MISTAKE_RATE = 0.25


def winner(b):
    for a, c, d in LINES:
        if b[a] and b[a] == b[c] == b[d]:
            return b[a]
    return "draw" if all(b) else None


def minimax(b, me):
    w = winner(b)
    if w == "O":
        return 1, None
    if w == "X":
        return -1, None
    if w == "draw":
        return 0, None
    best = (-2, None) if me == "O" else (2, None)
    for i in range(9):
        if not b[i]:
            b[i] = me
            score, _ = minimax(b, "X" if me == "O" else "O")
            b[i] = ""
            if (me == "O" and score > best[0]) or (me == "X" and score < best[0]):
                best = (score, i)
    return best


def bot_move(b):
    free = [i for i in range(9) if not b[i]]
    if random.random() < MISTAKE_RATE:
        return random.choice(free)
    return minimax(b, "O")[1]


def load():
    try:
        with open(STATE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"board": [""] * 9, "status": "playing", "wins": 0, "losses": 0, "draws": 0, "recent": []}


def render(s):
    issue = f"https://github.com/{REPO}/issues/new?body=Just+press+%22Create%22+%E2%80%94+the+board+updates+in+about+a+minute.&title="
    icon = {"X": "❌", "O": "⭕"}
    rows = []
    for r in range(3):
        cells = []
        for c in range(3):
            i = r * 3 + c
            v = s["board"][i]
            if v:
                cells.append(f'<td align="center" width="80" height="80"><h1>{icon[v]}</h1></td>')
            elif s["status"] == "playing":
                cells.append(f'<td align="center" width="80" height="80"><a href="{issue}ttt%7Cmove%7C{i}"><h1>⬜</h1></a></td>')
            else:
                cells.append('<td align="center" width="80" height="80"><h1>⬜</h1></td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    msg = {
        "playing": "<b>Your turn!</b> You are ❌. Click any ⬜ square to play — I'm ⭕ and I reply automatically.",
        "X": "🎉 <b>You beat me!</b> Respect.",
        "O": "🤖 <b>I won this round.</b> Want a rematch?",
        "draw": "🤝 <b>It's a draw!</b>",
    }[s["status"]]
    new = f'<a href="{issue}ttt%7Cnew"><img src="https://img.shields.io/badge/🔄_New_game-24c6dc?style=for-the-badge" alt="New game"/></a>'
    recent_html = ", ".join(f'<a href="https://github.com/{u}">@{u}</a>' for u in s["recent"][:5]) or "nobody yet — be the first!"
    return (
        f'{START}\n<p align="center">{msg}</p>\n'
        f'<table align="center">{"".join(rows)}</table>\n'
        f'<p align="center">{new}</p>\n'
        f'<p align="center"><sub>🏆 Humans won: <b>{s["wins"]}</b> · 🤖 Bot won: <b>{s["losses"]}</b> · 🤝 Draws: <b>{s["draws"]}</b>'
        f"<br/>Recent players: {recent_html}</sub></p>\n{END}"
    )


def write(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w") as f:
        json.dump(s, f, indent=2)
    with open(README) as f:
        text = f.read()
    text = re.sub(re.escape(START) + ".*?" + re.escape(END), lambda _: render(s), text, flags=re.S)
    with open(README, "w") as f:
        f.write(text)


def finish(s, result):
    s["status"] = result
    key = {"X": "wins", "O": "losses", "draw": "draws"}[result]
    s[key] += 1


def main(title, user):
    s = load()
    parts = title.strip().split("|")
    if parts[:2] == ["ttt", "new"]:
        s["board"], s["status"] = [""] * 9, "playing"
        reply = "New game started! Head back to the profile and make your move."
    elif parts[:2] == ["ttt", "move"] and len(parts) == 3 and parts[2].isdigit():
        i = int(parts[2])
        if s["status"] != "playing" or not 0 <= i <= 8 or s["board"][i]:
            print("That square isn't available — the board may have changed. Refresh the profile and try another one.")
            return
        s["board"][i] = "X"
        s["recent"] = [user] + [u for u in s["recent"] if u != user]
        result = winner(s["board"])
        if result:
            finish(s, result)
        else:
            s["board"][bot_move(s["board"])] = "O"
            result = winner(s["board"])
            if result:
                finish(s, result)
        reply = {
            "playing": "Move made, and I've replied. Your turn again on the profile!",
            "X": "You won! 🎉 Thanks for playing.",
            "O": "I won this one 🤖 — start a new game for a rematch.",
            "draw": "Draw! 🤝 Start a new game to go again.",
        }[s["status"]]
    else:
        print("Unrecognised game command.")
        return
    write(s)
    print(reply)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
