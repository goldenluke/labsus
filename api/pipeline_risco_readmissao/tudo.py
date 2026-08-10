import os

def juntar_arquivos_pasta_atual(extensoes=('.py', '.html'), arquivo_saida='resultado_junto.txt'):
    """
    Encontra todos os arquivos com as extensões especificadas na pasta atual
    (e subpastas) e os junta em um único arquivo de texto, ignorando
    pastas comuns de desenvolvimento.

    Argumentos:
        extensoes (tuple): Uma tupla de extensões de arquivo a serem detectadas (ex: ('.py', '.html')).
        arquivo_saida (str): O nome do arquivo que conterá o conteúdo combinado.
    """
    pasta_raiz = '.'
    arquivos_encontrados = 0
    pastas_a_ignorar = {'.venv', '__pycache__', '.git', 'node_modules'}

    caminho_absoluto_saida = os.path.abspath(arquivo_saida)
    # Garante que o script que está rodando também seja ignorado
    try:
        caminho_absoluto_script_atual = os.path.abspath(__file__)
    except NameError:
        # Se executado interativamente, __file__ não existe
        caminho_absoluto_script_atual = ''


    print(f"Analisando a pasta atual: '{os.getcwd()}'")
    print(f"Buscando por extensões: {list(extensoes)}")
    print(f"Pastas a ignorar: {list(pastas_a_ignorar)}")

    try:
        with open(arquivo_saida, 'w', encoding='utf-8') as outfile:
            for pasta_atual, subpastas, arquivos in os.walk(pasta_raiz):
                # --- LÓGICA PARA IGNORAR PASTAS ---
                # Modifica a lista de subpastas que o os.walk visitará
                subpastas[:] = [d for d in subpastas if d not in pastas_a_ignorar]

                for arquivo in sorted(arquivos): # Ordena os arquivos para um resultado consistente
                    if arquivo.endswith(extensoes):
                        caminho_completo = os.path.join(pasta_atual, arquivo)
                        caminho_absoluto_arquivo = os.path.abspath(caminho_completo)

                        # Ignora o próprio arquivo de saída e o script que está rodando
                        if caminho_absoluto_arquivo == caminho_absoluto_saida or \
                           caminho_absoluto_arquivo == caminho_absoluto_script_atual:
                            continue

                        print(f"  -> Adicionando o arquivo: {caminho_completo}")
                        arquivos_encontrados += 1

                        outfile.write(f'# === Início do arquivo: {caminho_completo} ===\n\n')
                        try:
                            with open(caminho_completo, 'r', encoding='utf-8', errors='ignore') as infile:
                                outfile.write(infile.read())
                            outfile.write(f'\n\n# === Fim do arquivo: {caminho_completo} ===\n\n')
                        except Exception as e:
                            outfile.write(f'# === Erro ao ler o arquivo: {caminho_completo} - {e} ===\n\n')

        if arquivos_encontrados > 0:
            print(f"\n✅ Sucesso! {arquivos_encontrados} arquivo(s) foram juntados em '{arquivo_saida}'.")
        else:
            print(f"\nNenhum arquivo com as extensões {list(extensoes)} foi encontrado para juntar.")
            # Remove o arquivo de saída se ele foi criado mas ficou vazio
            if os.path.exists(arquivo_saida):
                os.remove(arquivo_saida)

    except Exception as e:
        print(f"❌ Ocorreu um erro inesperado: {e}")

# --- Como usar ---
# 1. Salve este código como um arquivo .py (ex: juntar_tudo.py) na pasta raiz do seu projeto.
# 2. Execute-o a partir do terminal com: python juntar_tudo.py
if __name__ == "__main__":
    # Chama a função para juntar arquivos .py e .html
    juntar_arquivos_pasta_atual(extensoes=('.py', '.html'), arquivo_saida='codigo_completo.txt')
