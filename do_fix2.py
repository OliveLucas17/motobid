with open('/home/work/.openclaw/workspace/projects/motobid/monitor.py', 'rb') as f:
    lines = f.readlines()

# Replace lines 69 through 76 with clean version
new_lines = [
    b'    entry = {\n',
    b'        \"id\": lote_id + \"_\" + datetime.now().strftime(\"%Y%m%d%H%M%S\"),\n',
    b'        \"lote_id\": lote_id,\n',
    b'        \"tipo\": tipo,\n',
    b'        \"msg\": msg,\n',
    b'        \"ts\": datetime.now().isoformat(),\n',
    b'        \"lance\": lot_data.get(\"lance_atual\") if lot_data else None,\n',
    b'    }\n',
]

# Remove lines 69-70 (the broken dict entry) and insert clean version
# Line 69 index 68: entry = {
# Line 70 index 69:   'id': f'... broken
# So we replace indices 68-75 (entry = { through lance: ... })
lines = lines[:68] + new_lines + lines[76:]

with open('/home/work/.openclaw/workspace/projects/motobid/monitor.py', 'wb') as f:
    f.writelines(lines)
print('Done!')
