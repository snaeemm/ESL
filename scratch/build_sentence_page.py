import json

with open('/private/tmp/claude-501/-Users-shaz-MOI-Arabic-Sign-Language/009f236c-3b8b-4b60-ac1d-53f2ca7acc1d/scratchpad/sentence_b64.json') as f:
    v = json.load(f)

template = open('/Users/shaz/MOI-Arabic-Sign-Language/scratch/sentence_page_template.html').read()
html = (template
        .replace('__SENTENCE_SOURCE__', v['sentence_source'])
        .replace('__SENTENCE_CARTOON__', v['sentence_cartoon']))

with open('/Users/shaz/MOI-Arabic-Sign-Language/scratch/sentence_page.html', 'w') as f:
    f.write(html)

print('wrote', len(html), 'bytes')
