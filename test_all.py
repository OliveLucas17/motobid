import ast

files = ['auto_scout.py', 'config.py', 'monitor.py']
for f in files:
    try:
        ast.parse(open(f).read())
        print('OK:', f)
    except SyntaxError as e:
        print('FAIL:', f, 'line', e.lineno, ':', e.msg)
        break