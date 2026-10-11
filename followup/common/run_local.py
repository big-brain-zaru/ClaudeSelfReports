"""Local open-model runner (Ollama HTTP API). Fixed temperature and seed per call; raw output logged to JSONL."""
import hashlib
import json
import time
import urllib.request

OLLAMA = "http://127.0.0.1:11434/api/chat"


def chat(model, prompt, temperature=0.7, seed=0, num_predict=1024, system=None, timeout=1800):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body = {"model": model, "messages": msgs, "stream": False,
            "options": {"temperature": temperature, "seed": seed, "num_predict": num_predict}}
    req = urllib.request.Request(OLLAMA, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read())
    return {"model": model, "temperature": temperature, "seed": seed,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "text": out["message"]["content"], "eval_count": out.get("eval_count"),
            "seconds": round(time.time() - t0, 2), "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}


def log(path, rec):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def strip_think(text):
    """deepseek-r1 emits <think>...</think>; scoring uses only what follows."""
    return text.split("</think>")[-1].strip() if "</think>" in text else text.strip()
