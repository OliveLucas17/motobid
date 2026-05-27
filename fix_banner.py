with open('/home/work/.openclaw/workspace/projects/motobid/monitor.py', 'r') as f:
    content = f.read()

old = 'Filtro: SEM Honda/Yamaha/Shineray, COM documento, margem &gt;R$3k.'
new = 'Filtro: Honda/Yamaha TOP | Suzuki/Dafra ALTA | Exclui Shineray | COM documento'

if old in content:
    content = content.replace(old, new)
    print('Fixed full text')
elif 'SEM Honda' in content:
    content = content.replace('SEM Honda/Yamaha/Shineray', 'Honda/Yamaha TOP | Shineray Excluida')
    print('Fixed partial text')
else:
    print('Not found')

with open('/home/work/.openclaw/workspace/projects/motobid/monitor.py', 'w') as f:
    f.write(content)
print('Done')
