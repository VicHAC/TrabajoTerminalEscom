import os
import sys

def search_all_files(query):
    for root, dirs, files in os.walk('.'):
        if '.venv' in root or '.git' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for idx, line in enumerate(f, 1):
                            if query.lower() in line.lower():
                                print(f"{filepath}:{idx}: {line.strip()}")
                except Exception as e:
                    pass

if __name__ == '__main__':
    search_all_files(sys.argv[1])
