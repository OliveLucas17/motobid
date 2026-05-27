import ast
files = ['auto_scout.py', 'config.py', 'monitor.py']
all_ok = True
for f in files:
    try:
        ast.parse(open('/home/work/.openclaw/workspace/projects/motobid/' + f).read())
        print('OK:', f)
    except SyntaxError as e:
        print('FAIL:', f, 'line', e.lineno, ':', e.msg)
        all_ok = False
print('All OK' if all_ok else 'Has errors')