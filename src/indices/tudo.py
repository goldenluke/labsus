import os

def juntar_arquivos_pasta_atual(
    extensoes=(
        '.py', '.html', '.js', '.jsx', '.ts', '.tsx',
        '.css', '.astro', '.sh', '.md',
        '.yml', '.yaml'
    ),
    arquivo_saida='codigo_completo.txt',
    tamanho_max_mb=2
):
    pasta_raiz = '.'
    arquivos_encontrados = 0

    pastas_a_ignorar = {
        'venv',
        '.venv',
        'env',
        '__pycache__',
        '.git',
        'node_modules',
        '.mypy_cache',
        '.pytest_cache',
        'dist',
        'build',
        '.next',
        '.nuxt',
        '.output'
    }

    arquivos_a_ignorar = {
        '.lock',
        '.log',
        '.min.js',
        '.map',
        '.geojson',
        '.topojson'
    }

    # 🔥 caminhos/pastas específicas a ignorar
    caminhos_ignorados = [
        'frontend/public/geojson_uf/',
        'frontend/metaenv/',
        'src'
    ]

    tamanho_max_bytes = tamanho_max_mb * 1024 * 1024

    caminho_saida = os.path.abspath(arquivo_saida)

    try:
        caminho_script = os.path.abspath(__file__)
    except NameError:
        caminho_script = ""

    print(f"Pasta analisada: {os.getcwd()}")

    with open(arquivo_saida, 'w', encoding='utf-8') as outfile:

        for pasta_atual, subpastas, arquivos in os.walk(pasta_raiz):

            # 🔥 filtrar pastas padrão
            subpastas[:] = sorted([
                p for p in subpastas
                if p not in pastas_a_ignorar
                and not p.startswith('.')
            ])

            arquivos = sorted(arquivos)

            for arquivo in arquivos:

                if not arquivo.endswith(extensoes):
                    continue

                if any(arquivo.endswith(x) for x in arquivos_a_ignorar):
                    continue

                caminho = os.path.join(pasta_atual, arquivo)
                caminho_abs = os.path.abspath(caminho)
                caminho_rel = os.path.relpath(caminho)

                # 🚫 ignorar caminhos específicos (pastas inteiras)
                if any(p in caminho_rel for p in caminhos_ignorados):
                    print(f"Ignorando (pasta específica): {caminho_rel}")
                    continue

                if caminho_abs in (caminho_saida, caminho_script):
                    continue

                # 🚫 pular arquivos grandes
                try:
                    if os.path.getsize(caminho) > tamanho_max_bytes:
                        print(f"Pulando (muito grande): {caminho_rel}")
                        continue
                except Exception:
                    continue

                print(f"Adicionando: {caminho_rel}")
                arquivos_encontrados += 1

                outfile.write(f"\n\n{'='*80}\n")
                outfile.write(f"ARQUIVO: {caminho_rel}\n")
                outfile.write(f"{'='*80}\n\n")

                try:
                    with open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
                        for linha in f:
                            outfile.write(linha)
                except Exception as e:
                    outfile.write(f"\nErro ao ler arquivo: {e}\n")

    print(f"\n✔ {arquivos_encontrados} arquivos adicionados em {arquivo_saida}")


if __name__ == "__main__":
    juntar_arquivos_pasta_atual()
