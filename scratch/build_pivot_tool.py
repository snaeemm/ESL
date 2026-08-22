import json

data = json.load(open('/private/tmp/claude-501/-Users-shaz-MOI-Arabic-Sign-Language/009f236c-3b8b-4b60-ac1d-53f2ca7acc1d/scratchpad/pivot_tool_data.json'))

PIECES = [
    {"id": "left_upper_arm", "label": "Left upper arm", "points": ["shoulder", "elbow"]},
    {"id": "left_forearm", "label": "Left forearm", "points": ["elbow", "wrist"]},
    {"id": "right_upper_arm", "label": "Right upper arm", "points": ["shoulder", "elbow"]},
    {"id": "right_forearm", "label": "Right forearm", "points": ["elbow", "wrist"]},
    {"id": "left_open_palm", "label": "Left: Open palm", "points": ["wrist"]},
    {"id": "left_pointing", "label": "Left: Pointing", "points": ["wrist"]},
    {"id": "left_thumbs_up", "label": "Left: Thumbs up", "points": ["wrist"]},
    {"id": "right_open_palm", "label": "Right: Open palm", "points": ["wrist"]},
    {"id": "right_pointing", "label": "Right: Pointing", "points": ["wrist"]},
    {"id": "right_thumbs_up", "label": "Right: Thumbs up", "points": ["wrist"]},
]

images_js = json.dumps(data["images"])
sizes_js = json.dumps(data["sizes"])
pieces_js = json.dumps(PIECES)

cards_html = ""
for p in PIECES:
    cards_html += f'''
    <div class="card" id="card-{p['id']}" data-piece="{p['id']}">
      <div class="card-head">
        <span class="piece-label">{p['label']}</span>
        <span class="status" id="status-{p['id']}">0 / {len(p['points'])}</span>
      </div>
      <canvas id="canvas-{p['id']}"></canvas>
      <div class="hint" id="hint-{p['id']}"></div>
      <button class="reset-btn" data-reset="{p['id']}">Reset</button>
    </div>
    '''

template = open('/Users/shaz/MOI-Arabic-Sign-Language/scratch/pivot_tool_template.html').read()
html = (template
        .replace('__CARDS__', cards_html)
        .replace('__TOTAL__', str(len(PIECES)))
        .replace('__IMAGES_JSON__', images_js)
        .replace('__SIZES_JSON__', sizes_js)
        .replace('__PIECES_JSON__', pieces_js))

open('/Users/shaz/MOI-Arabic-Sign-Language/scratch/pivot_tool.html', 'w').write(html)
print('wrote', len(html), 'bytes')
