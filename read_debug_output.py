# read_debug_output.py
with open('debug_output.txt', 'rb') as f:
    content = f.read()
    print(content.decode('utf-8', errors='replace'))
