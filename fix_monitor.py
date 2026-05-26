with open('/home/work/.openclaw/workspace/projects/motobid/monitor.py', 'r') as f:
    content = f.read()

# Fix line 70: f-string with nested dict access
old = '        {\"id\": f\"{lote_id}_{datetime.now().strftime(\\\"%Y%m%d%H%M%S\\\")}\",\n        \"lote_id\": lote_id,\n        \"tipo\": tipo,\n        \"msg\": msg,'
new = '        {\"id\": str(lote_id) + \"_\" + datetime.now().strftime(\"%Y%m%d%H%M%S\"),\n        \"lote_id\": lote_id,\n        \"tipo\": tipo,\n        \"msg\": msg,'

if old in content:
    content = content.replace(old, new)
    print('Fixed line 70')
else:
    print('Pattern not found, trying alternate...')
    # Check what line 70 actually looks like as bytes
    with open('/home/work/.openclaw/workspace/projects/motobid/monitor.py', 'rb') as f:
        lines = f.readlines()
    print('Line 70:', repr(lines[69][:80]))
    print('Line 71:', repr(lines[70][:80]))

with open('/home/work/.openclaw/workspace/projects/motobid/monitor.py', 'w') as f:
    f.write(content)