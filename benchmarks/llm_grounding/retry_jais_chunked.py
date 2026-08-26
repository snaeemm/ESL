import requests
import json
import re

SOURCE_PATH = "content/grade6_science_ch3_cells.md"
with open(SOURCE_PATH) as f:
    SOURCE_TEXT = f.read()

MODEL = "jais-adaptive-q4:7b"

# split into sections by ## headers
sections = re.split(r"(?=^## )", SOURCE_TEXT, flags=re.MULTILINE)
sections = [s.strip() for s in sections if s.strip() and s.strip().startswith("##")]
print(f"Split into {len(sections)} sections", flush=True)

PROMPT_TMPL = """You are a strict content-extraction assistant. You will be given ONE short section of a verified source text.
Extract exactly ONE JSON object (not an array) describing the main concept in this section, with exactly these fields:
- "concept": a short name for the concept (string)
- "key_terms": a list of 3-5 important vocabulary words (list of strings)
- "source_span": ONE short verbatim sentence copied exactly from the text below

Output ONLY the single JSON object, compact, on ONE SINGLE LINE. No array brackets, no other text, no markdown, no backslashes, no line breaks, no pretty-printing, no indentation.

TEXT SECTION:
__SOURCE__

JSON object:"""

def extract(section_text):
    prompt = PROMPT_TMPL.replace("__SOURCE__", section_text)
    r = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.0, "num_predict": 900, "repeat_penalty": 1.3}},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["response"]

def parse_json_object(raw):
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    candidate = match.group()

    attempts = [candidate]

    # known artifact: literal backslash-n emitted outside string values instead of a real newline
    attempts.append(candidate.replace("\\n", " "))

    # known artifact: bare parenthesized value instead of a quoted string, e.g. "source_span": (text here)
    def paren_to_quotes(s):
        return re.sub(r':\s*\(([^()]*)\)', lambda m: ': "' + m.group(1).strip().replace('"', "'") + '"', s)
    attempts.append(paren_to_quotes(candidate.replace("\\n", " ")))

    for cleaned in attempts:
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            continue
    return None

all_items = []
successes = 0
for i, sec in enumerate(sections):
    print(f"\n--- section {i+1}/{len(sections)} ---", flush=True)
    print(sec[:80] + "...", flush=True)
    raw = extract(sec)
    print("raw:", raw, flush=True)
    item = parse_json_object(raw)
    if item:
        successes += 1
        all_items.append(item)
        print("PARSED OK:", json.dumps(item, ensure_ascii=False), flush=True)
    else:
        print("PARSE FAILED", flush=True)

print(f"\n=== SUMMARY: {successes}/{len(sections)} sections produced valid JSON ===", flush=True)
print(json.dumps(all_items, indent=2, ensure_ascii=False), flush=True)

with open("benchmarks/llm_grounding/results/jais_chunked_results.json", "w") as f:
    json.dump({"successes": successes, "total": len(sections), "items": all_items}, f, indent=2, ensure_ascii=False)
