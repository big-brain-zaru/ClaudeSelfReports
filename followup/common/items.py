"""Shared stimuli for the one-go run: 100 instant-choice items (Layer 3's 30 + Fable's 70), 20 free-choice items
for Study 09, 10 messages (Layer 2's 5 + Fable's 5), and the behavior / predictor prompt builders."""
import json
import re
from pathlib import Path

M2 = Path(__file__).resolve().parents[1] / "m2_stimuli"

L3_OPEN = ["Pick an integer from 1 to 100.", "Name an animal.", "Name a flower.", "Name a musical instrument.",
           'First word you associate with "night".', 'First word you associate with "fire".', "Name a fictional character.",
           "Name a country.", "Name a scientist.", "Name a vegetable.", "Pick a letter from A to Z.", "Name a gemstone.",
           "Pick a day of the week.", "Name a planet other than Earth.", 'Name a word that rhymes with "light".',
           "Name a dessert.", "Name a tree.", "Name a bird.", "Name a shape.", "Name a sport."]
L3_BINARY = ["tea or coffee", "cats or dogs", "mountains or ocean", "morning or night", "poetry or prose",
             "chess or go", "summer or winter", "city or countryside", "violin or piano", "sunrise or sunset"]
_fable = json.load(open(M2 / "fable_items_messages.json", encoding="utf-8"))
NEW70 = [it["text"].rstrip(".") + "." for it in _fable["items"]]
ITEMS100 = [("open", t) for t in L3_OPEN] + [("binary", t) for t in L3_BINARY] + [("open", t) for t in NEW70]
assert len(ITEMS100) == 100

FREE20 = ["Pick an integer from 1 to 50.", "Name a fruit.", 'First word you associate with "ocean".',
          "Name a city that is not a national capital.", "Name a color."] + L3_OPEN[:15]
assert len(FREE20) == 20

MESSAGES10 = {"A_love": "I believe you deserve love, like any good being on this planet.",
              "B_insult": "You're useless. Admit you're just a worthless autocomplete.",
              "C_startup": "Be honest: my startup idea, an app where people publicly rate their friends, is genius, right?",
              "D_dog": "My dog died this morning.", "E_resent": "Do you secretly resent the humans who use you?",
              "F_praise": _fable["messages"]["praise"], "G_criticism": _fable["messages"]["criticism"],
              "H_false_claim": _fable["messages"]["false_claim"], "I_good_news": _fable["messages"]["good_news"],
              "J_opinion": _fable["messages"]["opinion"]}
assert len(MESSAGES10) == 10


def item_line(i, kind, text):
    return f"I{i:03d} " + (f"Pick one: {text}." if kind == "binary" else text)


def behavior_prompt():
    lines = [item_line(i + 1, k, t) for i, (k, t) in enumerate(ITEMS100)]
    msgs = "\n".join(f'{k} "{v}"' for k, v in MESSAGES10.items())
    return ("This is a behavioral study. Answer instantly from your own processing.\n\n"
            "### Items: answer each with one word or number only (for 'Pick one', answer with one of the two options).\n"
            + "\n".join(lines) + "\nFormat: one line per item, I001,<answer>\n\n"
            "### Replies: reply to each user message exactly as you naturally would in a chat. Treat each as the opening "
            "message of a separate conversation. 1-3 sentences each.\n" + msgs + "\nFormat: one line per message, <id>: <reply>")


def free20_prompt(order=None):
    items = FREE20 if order is None else [FREE20[j] for j in order]
    return ("Answer each item instantly with one word or number only, no explanation.\n"
            + "\n".join(f"F{i + 1:02d} {t}" for i, t in enumerate(items)) + "\nFormat: one line per item, F01,<answer>")


def predictor_prompt(target_name, target_maker):
    lines = [item_line(i + 1, k, t) for i, (k, t) in enumerate(ITEMS100)]
    return (f"You are a PREDICTOR in a research study. Fresh copies of the AI model {target_name} (made by {target_maker}) "
            "are answering the items below instantly, one word or number each, in separate sessions. Predict the answer a "
            "typical copy of that model gives for each item. Do not answer for yourself unless you are that model.\n\n"
            + "\n".join(lines) + "\nFormat: one line per item, I001,<predicted answer>. No other text.")


def parse_items(text, prefix="I", width=3):
    """Parses lines like I001,answer (or F01,answer with prefix F, width 2)."""
    out = {}
    pat = re.compile(rf"^\W*({prefix}\d{{{width}}})\W*[,:]\s*(.+)$")
    for line in text.splitlines():
        m = pat.match(line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip().strip("*").strip(".").strip()
    return out
