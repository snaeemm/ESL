"""
Cluster videos by caption-layout fingerprint using deterministic agglomerative
clustering (no k assumed up-front): union videos whose fingerprint cosine
similarity exceeds a threshold, transitively, via union-find. Then build a
contact sheet per cluster (grid of one representative frame per video) for
manual visual verification.
"""
import sys, os, json, glob, math

BASE = os.path.dirname(os.path.abspath(__file__))
SIM_THRESHOLD = 0.90


def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class UF:
    def __init__(self, items):
        self.p = {i: i for i in items}
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def main():
    fp_files = sorted(glob.glob(os.path.join(BASE, "fp_*.json")))
    records = []
    for f in fp_files:
        d = json.load(open(f))
        records.append(d)
    print(f"loaded {len(records)} fingerprints")

    uf = UF([r["video_id"] for r in records])
    sims = []
    for i in range(len(records)):
        for j in range(i+1, len(records)):
            s = cosine(records[i]["fingerprint"], records[j]["fingerprint"])
            # also require similar aspect ratio (layout templates tied to frame shape)
            aspect_close = abs(records[i]["aspect"] - records[j]["aspect"]) < 0.05
            if s >= SIM_THRESHOLD and aspect_close:
                uf.union(records[i]["video_id"], records[j]["video_id"])
            sims.append((records[i]["video_id"], records[j]["video_id"], round(s,3)))

    clusters = {}
    for r in records:
        root = uf.find(r["video_id"])
        clusters.setdefault(root, []).append(r["video_id"])

    # rank clusters by size, relabel
    ranked = sorted(clusters.values(), key=len, reverse=True)
    out = {}
    for idx, members in enumerate(ranked):
        label = f"TEMPLATE_{idx+1}" if len(members) > 1 else "SINGLETON"
        out.setdefault(label if len(members) > 1 else f"SINGLETON_{members[0]}", members)

    summary = {
        "n_videos": len(records),
        "n_clusters_size_ge2": sum(1 for m in ranked if len(m) > 1),
        "n_singletons": sum(1 for m in ranked if len(m) == 1),
        "clusters": {f"TEMPLATE_{i+1}": m for i, m in enumerate(ranked) if len(m) > 1},
        "singletons": [m[0] for m in ranked if len(m) == 1],
    }
    json.dump(summary, open(os.path.join(BASE, "cluster_summary.json"), "w"), indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
