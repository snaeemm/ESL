import requests
import json
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

SOURCE_PATH = "/Users/shaz/MOI-Arabic-Sign-Language/content/grade6_science_ch3_cells.md"
with open(SOURCE_PATH) as f:
    SOURCE_TEXT = f.read()

MODEL = "jais-adaptive-q4:7b"

FEWSHOT_PROMPT = """You are a strict content-extraction assistant. You will be given a verified source text.
Extract the key educational concepts as a structured JSON array. Each item must have exactly these fields:
- "concept": a short name for the concept (string)
- "key_terms": a list of important vocabulary words for this concept (list of strings, keep this list SHORT, 3-5 words max)
- "source_span": a short VERBATIM quote (one sentence, copied exactly) from the source text that supports this concept

Rules:
- Only use information that is literally present in the source text. Do not add outside knowledge.
- "source_span" MUST be an exact substring of the source text, one sentence only.
- Output ONLY a JSON array, no other text, no markdown code fences, no backslashes.
- Keep it short: extract at most 5 concepts.

Example of the exact format expected (for a different, unrelated text about volcanoes):
[
{"concept": "What is a volcano?", "key_terms": ["volcano", "mountain", "eruption"], "source_span": "A volcano is a mountain that can erupt."},
{"concept": "Types of lava", "key_terms": ["lava", "magma", "flow"], "source_span": "Lava is melted rock that flows from a volcano."}
]

Now do the same for this source text.

SOURCE TEXT:
__SOURCE__

JSON array:"""

def extract():
    prompt = FEWSHOT_PROMPT.replace("__SOURCE__", SOURCE_TEXT)
    r = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.0, "num_predict": 3000, "repeat_penalty": 1.3}},
        timeout=300,
    )
    r.raise_for_status()
    return r.json()["response"]

def parse_json_array(raw):
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None

def score(model_output_text, items):
    vec = TfidfVectorizer().fit([SOURCE_TEXT, model_output_text])
    vecs = vec.transform([SOURCE_TEXT, model_output_text])
    cos = cosine_similarity(vecs[0], vecs[1])[0][0]
    rscorer = rouge_scorer.RougeScorer(["rouge1", "rougeL"], use_stemmer=True)
    rouge = rscorer.score(SOURCE_TEXT, model_output_text)
    src_tokens = set(re.findall(r"\w+", SOURCE_TEXT.lower()))
    out_tokens = set(re.findall(r"\w+", model_output_text.lower()))
    jaccard = len(src_tokens & out_tokens) / len(src_tokens | out_tokens) if (src_tokens | out_tokens) else 0
    src_ref = re.findall(r"\w+", SOURCE_TEXT.lower())
    out_cand = re.findall(r"\w+", model_output_text.lower())
    smoothie = SmoothingFunction().method4
    bleu = sentence_bleu([src_ref], out_cand, smoothing_function=smoothie) if out_cand else 0
    span_matches = 0
    span_total = 0
    if items:
        for item in items:
            span = item.get("source_span", "") if isinstance(item, dict) else ""
            if span:
                span_total += 1
                if span.strip() in SOURCE_TEXT:
                    span_matches += 1
    span_match_rate = span_matches / span_total * 100 if span_total else 0
    return {
        "cosine_similarity": round(float(cos), 4),
        "rouge1_f1": round(rouge["rouge1"].fmeasure, 4),
        "rougeL_f1": round(rouge["rougeL"].fmeasure, 4),
        "jaccard": round(jaccard, 4),
        "bleu": round(bleu, 4),
        "source_span_verbatim_match_rate_pct": round(span_match_rate, 1),
        "num_concepts_extracted": len(items) if items else 0,
        "json_parsed_successfully": items is not None,
    }

print(f"=== {MODEL} (few-shot retry) ===", flush=True)
raw = extract()
print("--- raw output ---", flush=True)
print(raw, flush=True)
items = parse_json_array(raw)
flat_text = json.dumps(items, ensure_ascii=False) if items else raw
metrics = score(flat_text, items)
print("--- metrics ---", flush=True)
print(json.dumps(metrics, indent=2, ensure_ascii=False), flush=True)
