import json, sys, os

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

path = sys.argv[1]
with open(path, encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    try:
        entry = json.loads(line)
    except:
        continue
    etype = entry.get('type', '?')

    if etype in ('user', 'assistant', 'message'):
        msg = entry.get('message', {})
        role = msg.get('role', etype)
        content = msg.get('content', entry.get('content', ''))

        if isinstance(content, list):
            parts = []
            for b in content:
                if isinstance(b, dict):
                    if b.get('type') == 'text':
                        parts.append(b['text'][:3000])
                    elif b.get('type') == 'tool_use':
                        inp = json.dumps(b.get('input', {}), ensure_ascii=True)[:500]
                        parts.append('[TOOL: %s -> %s]' % (b.get('name', '?'), inp))
                    elif b.get('type') == 'tool_result':
                        rc = b.get('content', '')
                        if isinstance(rc, list):
                            for rb in rc:
                                if isinstance(rb, dict) and rb.get('type') == 'text':
                                    parts.append('[RESULT: %s]' % rb['text'][:500])
                        elif isinstance(rc, str):
                            parts.append('[RESULT: %s]' % rc[:500])
            content = '\n'.join(parts)

        if isinstance(content, str) and len(content.strip()) > 0:
            print('--- [%d] %s ---' % (i, role))
            print(content[:4000])
            print()
