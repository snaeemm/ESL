import requests
import json
import re
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

SOURCE_PATH = "content/grade6_science_ch3_cells.md"

with open(SOURCE_PATH) as f:
    SOURCE_TEXT = f.read()

MODELS = [
    "qwen3:latest",
    "hf.co/tiiuae/Falcon-H1-7B-Instruct-GGUF:Q4_K_M",
    "jais-adaptive-q4:7b",
    "qwen3.5-9b:q4",
]

SYSTEM_PROMPT = """You are a strict content-extraction assistant. You will be given a verified source text.
Extract the key educational concepts as a structured JSON array. Each item must have exactly these fields:
- "concept": a short name for the concept (string)
- "key_terms": a list of important vocabulary words for this concept (list of strings)
- "source_span": a VERBATIM quote copied exactly from the source text that supports this concept (string)

Rules:
- Only use information that is literally present in the source text. Do not add outside knowledge.
- "source_span" MUST be an exact substring of the source text, character for character.
- Output ONLY a JSON array, no other text, no markdown code fences.
"""

def extract(model):
    prompt = f"{SYSTEM_PROMPT}\n\nSOURCE TEXT:\n{SOURCE_TEXT}\n\nJSON array:"
    r = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False, "think": False, "options": {"temperature": 0.0, "num_predict": 6000, "repeat_penalty": 1.3}},
        timeout=300,
    )
    r.raise_for_status()
    return r.json()["response"]

def parse_json_array(raw):
    # strip <think> blocks some models emit
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    # try to find the JSON array in the text
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None

def score(model_output_text, items):
    # cosine similarity (TF-IDF) between concatenated extraction and source
    vec = TfidfVectorizer().fit([SOURCE_TEXT, model_output_text])
    vecs = vec.transform([SOURCE_TEXT, model_output_text])
    cos = cosine_similarity(vecs[0], vecs[1])[0][0]

    # ROUGE
    rscorer = rouge_scorer.RougeScorer(["rouge1", "rougeL"], use_stemmer=True)
    rouge = rscorer.score(SOURCE_TEXT, model_output_text)

    # Jaccard (token set overlap)
    src_tokens = set(re.findall(r"\w+", SOURCE_TEXT.lower()))
    out_tokens = set(re.findall(r"\w+", model_output_text.lower()))
    jaccard = len(src_tokens & out_tokens) / len(src_tokens | out_tokens) if (src_tokens | out_tokens) else 0

    # BLEU (source as reference, extraction as candidate)
    src_ref = re.findall(r"\w+", SOURCE_TEXT.lower())
    out_cand = re.findall(r"\w+", model_output_text.lower())
    smoothie = SmoothingFunction().method4
    bleu = sentence_bleu([src_ref], out_cand, smoothing_function=smoothie) if out_cand else 0

    # source_span verbatim-match rate (traceability check, direct measure of the brief's core requirement)
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

results = {}
for model in MODELS:
    print(f"=== {model} ===", flush=True)
    try:
        raw = extract(model)
    except Exception as e:
        print(f"  ERROR calling model: {e}", flush=True)
        results[model] = {"error": str(e)}
        continue
    items = parse_json_array(raw)
    flat_text = json.dumps(items, ensure_ascii=False) if items else raw
    metrics = score(flat_text, items)
    results[model] = metrics
    print(f"  {json.dumps(metrics, indent=2, ensure_ascii=False)}", flush=True)
    with open(f"benchmarks/llm_grounding/results/ch3_extraction_{model.replace('/', '_').replace(':', '_')}.json", "w") as f:
        json.dump({"raw_response": raw, "parsed_items": items}, f, indent=2, ensure_ascii=False)

print("\n=== FINAL RESULTS (all models) ===", flush=True)
print(json.dumps(results, indent=2, ensure_ascii=False), flush=True)
