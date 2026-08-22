import json

with open('/private/tmp/claude-501/-Users-shaz-MOI-Arabic-Sign-Language/009f236c-3b8b-4b60-ac1d-53f2ca7acc1d/scratchpad/video_b64_v2.json') as f:
    v = json.load(f)

template = open('/Users/shaz/MOI-Arabic-Sign-Language/scratch/unify_page_template.html').read()
html = (template
        .replace('__ALIF_SOURCE__', v['alif_source'])
        .replace('__ALIF_CARTOON__', v['alif_cartoon'])
        .replace('__INSIDE_SOURCE__', v['inside_source'])
        .replace('__INSIDE_CARTOON__', v['inside_cartoon']))

with open('/Users/shaz/MOI-Arabic-Sign-Language/scratch/unify_page.html', 'w') as f:
    f.write(html)

print('wrote', len(html), 'bytes')
