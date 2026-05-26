import re

with open('/home/work/.openclaw/workspace/projects/motobid/monitor.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

fix_count = 0
new_lines = []

for line in lines:
    orig = line
    # Fix f-strings with nested dict access like f'{entry['tipo']}'
    # Pattern: f'...{something['key']}...'
    # Replace with simple string concatenation or variable
    if 'f{' in line and '[' in line and line.strip().startswith('#') is False:
        # Try to compile it
        try:
            compile(line, '<string>', 'eval')
            new_lines.append(line)
        except SyntaxError:
            # Rewrite: replace dict['key'] with a temp variable approach
            # Find dict.key patterns and replace with safe versions
            newline = line
            # Replace patterns like entry['tipo'] -> entry_tipo
            # Simple approach: just rewrite the f-string as string concatenation
            
            # Pattern: f'...{expr['key']}...' -> need to change expr['key']
            # Use re to find and replace dict[...] inside f{}
            
            # Replace f-strings with dict access with a placeholder approach
            # Example: f'{emoji.get(entry['tipo'], '📢')}' -> f'{emoji.get(entry_tipo, '📢')}'
            # But easier: just use .get() and pass variables
            
            # Most aggressive: just comment out the line and replace with simpler version
            if 'msg[\"Subject\"]' in line or 'msg[\"subject\"]' in line.lower():
                # Extract parts
                if 'emoji.get' in line and 'tipos.get' in line:
                    # Complex line: f'{emoji.get(entry['tipo'], 'X')} [MotoBid] {tipos.get(entry['tipo'], entry['tipo'])} — {entry['lote_id']}'
                    # Simplify: just use static prefix + variables
                    newline = '        msg[\"Subject\"] = emoji.get(entry.get(\"tipo\"), \"\") + \" [MotoBid] \" + tipos.get(entry.get(\"tipo\"), \"\") + \" - \" + str(entry.get(\"lote_id\", \"\"))\n'
                    fix_count += 1
            elif 'log(f' in line and '[' in line:
                # log(f'...{var['key']}...') 
                # Simplify log line
                newline = '        log(\"[ALERTA] \" + tipo + \" \" + lote_id + \": \" + msg)\n'
                fix_count += 1
            else:
                new_lines.append('# ' + orig)
                new_lines.append('        pass  # rewrite needed\n')
                fix_count += 1
                continue
    else:
        new_lines.append(line)
        
print('Fixed', fix_count, 'lines')

new_text = ''.join(new_lines)
try:
    compile(new_text, '<string>', 'exec')
    print('SYNTAX OK!')
except SyntaxError as e:
    print('Line', e.lineno, ':', e.msg)
    nl = new_text.split('\n')
    for i in range(max(0, e.lineno-1), min(len(nl), e.lineno+3)):
        print(i+1, ':', repr(nl[i]))

with open('/home/work/.openclaw/workspace/projects/motobid/monitor.py', 'w', encoding='utf-8') as f:
    f.write(new_text)
