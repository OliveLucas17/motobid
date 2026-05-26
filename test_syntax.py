import ast, sys

files = [
    'auto_scout.py',
    'monitor.py',
    'config.py',
    'crawlers/__init__.py',
    'crawlers/sumare.py',
    'crawlers/ricoleiloes.py',
    'crawlers/hastasp.py',
]

for f in files:
    try:
        ast.parse(open(f).read())
        print('OK:', f)
    except SyntaxError as e:
        print('FAIL:', f, 'line', e.lineno, ':', e.msg)
        sys.exit(1)

print('\nTodos os arquivos OK!')