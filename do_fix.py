with open('/home/work/.openclaw/workspace/projects/motobid/monitor.py', 'rb') as f:
    lines = f.readlines()

old_line = lines[69]
new_line = b'        {\"id\": lote_id + \"_\" + datetime.now().strftime(\"%Y%m%d%H%M%S\"),\n'

print('OLD:', repr(old_line))
print('NEW:', repr(new_line))

lines[69] = new_line

with open('/home/work/.openclaw/workspace/projects/motobid/monitor.py', 'wb') as f:
    f.writelines(lines)
print('Done!')
