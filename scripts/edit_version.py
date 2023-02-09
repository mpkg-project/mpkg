with open('mpkg/__init__.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("-dev'", "'")
print(text)
with open('mpkg/__init__.py', 'w', encoding='utf-8') as f:
    f.write(text)
