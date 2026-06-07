import sys

def search_file(filename, query):
    with open(filename, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f, 1):
            if query.lower() in line.lower():
                print(f"{idx}: {line.strip()}")

if __name__ == '__main__':
    search_file('vistas/base_analisis.py', sys.argv[1])
