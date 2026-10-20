import json, sys, os

path = sys.argv[1]
with open(path, encoding='utf-8', errors='replace') as f:
    for i, line in enumerate(f):
        try:
            entry = json.loads(line)
        except:
            continue
        etype = entry.get('type', 'unknown')
        if etype == 'message':
            msg = entry.get('message', {})
            role = msg.get('role', '?')
            content = msg.get('content', '')
            if isinstance(content, list):
                texts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get('type') == 'text':
                            t = block['text'][:3000]
                            texts.append(t)
                        elif block.get('type') == 'tool_use':
                            inp = json.dumps(block.get('input', {}), ensure_ascii=True)[:300]
                            texts.append('[TOOL: %s(%s)]' % (block.get('name', '?'), inp))
                content = '\n'.join(texts)
            elif isinstance(content, str):
                content = content[:3000]
            safe = content[:4000].encode('ascii', 'replace').decode('ascii')
            print('=== Line %d: %s / %s ===' % (i, etype, role))
            print(safe)
            print()
