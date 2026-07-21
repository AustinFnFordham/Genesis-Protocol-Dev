try:
    with open('debug_save.txt', 'r', encoding='utf-16') as f:
        content = f.read()
except:
    with open('debug_save.txt', 'r', encoding='utf-8') as f:
        content = f.read()

with open('debug_utf8.txt', 'w', encoding='utf-8') as f:
    f.write(content)
print("Converted.")
