#!/usr/bin/env python3
"""
Conversor de JSON do GitHub para CSV - Processa cada arquivo individualmente
Cada arquivo JSON gera um arquivo CSV correspondente com o mesmo nome
FORMATO BRASILEIRO: vírgula como separador decimal, sem separador de milhar
INCLUI: Análise estatística descritiva no final do CSV
Autor: Mayk Moreira
Data: 2025
"""

import json
import csv
import sys
import glob
import os
import locale
import re
import estatisticas
from datetime import datetime

# Configura locale para formato brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass

# ==============================================
# FUNÇÕES DE FORMATAÇÃO DE NÚMEROS
# ==============================================

def format_decimal_br(number, decimal_places=2):
    """Formata número no padrão brasileiro: vírgula como decimal, sem separador de milhar"""
    if number is None:
        return ""
    
    # Converte para float se for string
    if isinstance(number, str):
        try:
            # Tenta converter, tratando tanto ponto quanto vírgula como decimal
            number = float(number.replace(',', '.').replace(' ', ''))
        except:
            return number
    
    # Formata sem separador de milhar e com vírgula como decimal
    formatted = f"{number:.{decimal_places}f}"
    
    # Substitui ponto por vírgula
    formatted = formatted.replace('.', ',')
    
    return formatted

# ==============================================
# FUNÇÕES DE EXTRAÇÃO DE DADOS
# ==============================================

def extract_all_modules(pr: dict) -> list:
    """Extrai todos os módulos únicos de um PR baseado nos arquivos alterados"""
    modules = set()
    
    if pr.get('files', {}).get('nodes'):
        for file_node in pr['files']['nodes']:
            try:
                file_path = file_node.get('path', '')
                if file_path:
                    # Pega o primeiro diretório como módulo
                    if '/' in file_path:
                        module = file_path.split('/')[0]
                        modules.add(module)
                    else:
                        modules.add('root')
            except:
                continue
    
    return sorted(list(modules))

def extract_commit_messages(pr: dict) -> str:
    """Extrai todas as mensagens de commit de um PR"""
    messages = []
    
    if pr.get('commits', {}).get('nodes'):
        for commit_node in pr['commits']['nodes']:
            try:
                commit = commit_node.get('commit', {})
                message = commit.get('message', '').strip()
                if message:
                    # Remove linhas em branco extras e limpa
                    clean_message = ' '.join(message.splitlines())
                    messages.append(clean_message)
            except:
                continue
    
    return ' | '.join(messages)

# ==============================================
# FUNÇÃO PRINCIPAL DE PROCESSAMENTO
# ==============================================

def process_json_file(json_file: str):
    """Processa um único arquivo JSON e gera um arquivo CSV correspondente"""
    print(f"Processando: {os.path.basename(json_file)}")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ERRO: Não foi possível ler o arquivo - {e}")
        return None
    
    prs = data.get("pull_requests", [])
    
    if not prs:
        print(f"  AVISO: Nenhum PR encontrado")
        return None
    
    # Gera nome do arquivo CSV baseado no JSON
    base_name = os.path.basename(json_file)
    output_base = base_name.rsplit('.', 1)[0]
    output_file = output_base + '.csv'
    save_path = "data/processed/"
    
    # Define as colunas do CSV (nova ordem)
    fieldnames = [
        'pr_number', 'created_at', 'merged_at',
        'time_to_merge_hours',  # AGORA em formato decimal brasileiro
        'changed_files', 'lines_changed',
        'total_comments', 'total_reviews',
        'pr_title', 'pr_body',
        'has_changes_requested',
        'main_module',         # Após has_changes_requested
        'cross_modules',       # Nova coluna
        'labels_list', 
        'inferred_task_type',
        'commit_messages'      # Nova coluna
    ]
    
    # Listas para coleta de dados para análise
    tempos_merge = []
    arquivos_alterados = []
    linhas_modificadas = []
    
    # Processa cada PR e escreve no CSV
    with open(save_path+output_file, 'w', newline='', encoding='utf-8') as csvfile:
        # Usa delimitador ponto-e-vírgula para melhor compatibilidade com Excel/Sheets BR
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        
        for pr in prs:
            try:
                # Cálculo do tempo em horas (AGORA como número decimal no formato brasileiro)
                time_formatted = ''
                time_hours_decimal = 0
                
                if pr.get('createdAt') and pr.get('mergedAt'):
                    try:
                        created = datetime.fromisoformat(pr['createdAt'].replace('Z', '+00:00'))
                        merged = datetime.fromisoformat(pr['mergedAt'].replace('Z', '+00:00'))
                        duration = merged - created
                        
                        # Calcula como número decimal (em horas)
                        time_hours_decimal = duration.total_seconds() / 3600
                        
                        # Formata no padrão brasileiro com 2 casas decimais
                        time_formatted = format_decimal_br(time_hours_decimal, 2)
                        
                    except Exception as e:
                        print(f"  AVISO: Erro ao calcular tempo do PR #{pr.get('number')}: {e}")
                        time_formatted = '0,00'
                        time_hours_decimal = 0.0
                else:
                    time_formatted = '0,00'
                    time_hours_decimal = 0.0
                
                # Coleta dados para análise
                if time_hours_decimal > 0:
                    tempos_merge.append(time_hours_decimal)
                
                # Extrai módulo principal (primeiro arquivo)
                main_module = ''
                if pr.get('files', {}).get('nodes'):
                    try:
                        first_file = pr['files']['nodes'][0]['path']
                        main_module = first_file.split('/')[0] if '/' in first_file else 'root'
                    except:
                        main_module = 'unknown'
                
                # Extrai todos os módulos (nova coluna)
                all_modules = extract_all_modules(pr)
                cross_modules_str = ', '.join(all_modules)
                
                # Se main_module não estiver na lista, adiciona
                if main_module and main_module not in all_modules:
                    all_modules.append(main_module)
                    cross_modules_str = ', '.join(sorted(all_modules))
                
                # Se não encontrou módulos, usa o principal
                if not cross_modules_str and main_module:
                    cross_modules_str = main_module
                
                # Extrai mensagens de commit (nova coluna)
                commit_messages = extract_commit_messages(pr)
                
                # Verifica se houve changes requested
                has_changes = 'FALSE'
                if pr.get('reviews', {}).get('nodes'):
                    for review in pr['reviews']['nodes']:
                        if review.get('state') == 'CHANGES_REQUESTED':
                            has_changes = 'TRUE'
                            break
                
                # Lista de labels
                labels = []
                if pr.get('labels', {}).get('nodes'):
                    labels = [label['name'] for label in pr['labels']['nodes']]
                
                # Infere tipo de tarefa (expansão de palavras-chave)
                task_type = 'other'
                title_lower = pr.get('title', '').lower()
                
                # Palavras-chave expandidas para melhor classificação
                bugfix_keywords = ['fix', 'bug', 'correction', 'error', 'issue', 'fail', 'broken', 'typo']
                feature_keywords = ['feat', 'add', 'implement', 'new', 'feature', 'support', 'create', 'introduce']
                refactor_keywords = ['refactor', 'cleanup', 'optimize', 'improve', 'restructure', 'rework', 'modernize']
                docs_keywords = ['doc', 'readme', 'changelog', 'documentation', 'comment', 'javadoc', 'manual']
                test_keywords = ['test', 'coverage', 'unit', 'integration', 'testing', 'spec']
                ci_keywords = ['build', 'ci', 'cd', 'pipeline', 'github', 'action', 'workflow', 'docker']
                
                if any(word in title_lower for word in bugfix_keywords):
                    task_type = 'bugfix'
                elif any(word in title_lower for word in feature_keywords):
                    task_type = 'feature'
                elif any(word in title_lower for word in refactor_keywords):
                    task_type = 'refactor'
                elif any(word in title_lower for word in docs_keywords):
                    task_type = 'docs'
                elif any(word in title_lower for word in test_keywords):
                    task_type = 'test'
                elif any(word in title_lower for word in ci_keywords):
                    task_type = 'ci'
                
                # Formata números no padrão brasileiro
                changed_files_val = pr.get('changedFiles', 0)
                changed_files = format_decimal_br(changed_files_val, 0)  # Sem casas decimais para contagens
                arquivos_alterados.append(changed_files_val)
                
                lines_changed_val = pr.get('additions', 0) + pr.get('deletions', 0)
                lines_changed = format_decimal_br(lines_changed_val, 0)
                linhas_modificadas.append(lines_changed_val)
                
                total_comments = format_decimal_br(pr.get('comments', {}).get('totalCount', 0), 0)
                total_reviews = format_decimal_br(pr.get('reviews', {}).get('totalCount', 0), 0)
                
                # Cria linha do CSV
                row_data = {
                    'pr_number': pr.get('number', ''),                    
                    'created_at': pr.get('createdAt', ''),
                    'merged_at': pr.get('mergedAt', ''),
                    'time_to_merge_hours': time_formatted,  # AGORA: formato decimal brasileiro
                    'changed_files': changed_files,  # Formato BR
                    'lines_changed': lines_changed,  # Formato BR
                    'total_comments': total_comments,  # Formato BR
                    'total_reviews': total_reviews,  # Formato BR
                    'pr_title': pr.get('title', ''),
                    'pr_body': re.sub(r'[\r\n]+', '', pr.get('bodyText', '')),
                    'has_changes_requested': has_changes,
                    'main_module': main_module,
                    'cross_modules': cross_modules_str,
                    'labels_list': ', '.join(labels),
                    'inferred_task_type': task_type,
                    'commit_messages': commit_messages
                }
                
                writer.writerow(row_data)
                
            except Exception as e:
                print(f"  ERRO ao processar PR #{pr.get('number', 'unknown')}: {e}")
                continue
        
        # ==============================================
        # SEÇÃO DE ANÁLISE ESTATÍSTICA
        # ==============================================
        
        # Calcula estatísticas para cada variável
        if tempos_merge or arquivos_alterados or linhas_modificadas:
            # Escreve cabeçalho da seção de análise
            csvfile.write('\n')
            csvfile.write(';' * 5 + ' ANÁLISE ESTATÍSTICA DESCRITIVA ' + ';' * 5 + '\n')
            csvfile.write('\n')
            
            # Função auxiliar para escrever estatísticas
            def escrever_estatisticas(csvfile, titulo, dados, unidade=''):
                if not dados:
                    return
                
                resumo = estatisticas.resumo_estatistico_completo(dados)
                
                # Cabeçalho da variável
                csvfile.write(f';### {titulo.upper()} ({unidade}) ###\n')
                
                # 1. ESTATÍSTICAS DESCRITIVAS BÁSICAS
                csvfile.write(';--- ESTATÍSTICAS DESCRITIVAS BÁSICAS ---\n')
                csvfile.write(f';Número de observações (n);{resumo["contagem"]}\n')
                csvfile.write(f';Mínimo;{format_decimal_br(resumo["minimo"], 2)}\n')
                csvfile.write(f';Máximo;{format_decimal_br(resumo["maximo"], 2)}\n')
                csvfile.write(f';Amplitude total;{format_decimal_br(resumo["amplitude_total"], 2)}\n')
                csvfile.write(f';Média aritmética (μ);{format_decimal_br(resumo["media"], 2)}\n')
                csvfile.write(f';Mediana;{format_decimal_br(resumo["mediana"], 2)}\n')
                
                # 2. MEDIDAS DE DISPERSÃO
                csvfile.write(';--- MEDIDAS DE DISPERSÃO ---\n')
                csvfile.write(f';Desvio padrão amostral (s);{format_decimal_br(resumo["desvio_padrao"], 2)}\n')
                csvfile.write(f';Variância;{format_decimal_br(resumo["variancia"], 2)}\n')
                csvfile.write(f';Coeficiente de variação;{format_decimal_br(resumo["coeficiente_variacao"], 2)}%\n')
                csvfile.write(f';Amplitude Interquartil (AIQ);{format_decimal_br(resumo["amplitude_interquartil"], 2)}\n')
                
                # 3. QUARTIS E PERCENTIS
                csvfile.write(';--- QUARTIS E PERCENTIS ---\n')
                csvfile.write(f';Percentil 10%;{format_decimal_br(resumo["percentil_10"], 2)}\n')
                csvfile.write(f';Percentil 25% (Q1);{format_decimal_br(resumo["percentil_25"], 2)}\n')
                csvfile.write(f';Percentil 50% (Mediana);{format_decimal_br(resumo["mediana"], 2)}\n')
                csvfile.write(f';Percentil 75% (Q3);{format_decimal_br(resumo["percentil_75"], 2)}\n')
                csvfile.write(f';Percentil 90%;{format_decimal_br(resumo["percentil_90"], 2)}\n')
                
                # 4. IDENTIFICAÇÃO DE OUTLIERS (TUKEY)
                csvfile.write(';--- IDENTIFICAÇÃO DE OUTLIERS (CRITÉRIO DE TUKEY, 1977) ---\n')
                csvfile.write(f';Limite inferior (Q1 - 1,5 × AIQ);{format_decimal_br(resumo["limite_inferior_tukey"], 2)}\n')
                csvfile.write(f';Limite superior (Q3 + 1,5 × AIQ);{format_decimal_br(resumo["limite_superior_tukey"], 2)}\n')
                csvfile.write(f';Número de outliers;{resumo["contagem_outliers"]}\n')
                csvfile.write(f';Percentual de outliers;{format_decimal_br(resumo["percentual_outliers"], 2)}%\n')
                
                # 5. CLASSIFICAÇÃO POR PERCENTIS (HINDMAN E FAN)
                csvfile.write(';--- CLASSIFICAÇÃO POR PERCENTIS (HINDMAN E FAN, 1996) ---\n')
                
                # Define pontos de corte baseados nos percentis
                p10 = resumo['percentil_10']
                p25 = resumo['percentil_25']
                p50 = resumo['mediana']
                p75 = resumo['percentil_75']
                p90 = resumo['percentil_90']
                
                csvfile.write(';Faixa;Classificação;Intervalo\n')
                csvfile.write(f';Muito Baixa;0% a 10%;≤ {format_decimal_br(p10, 2)}\n')
                csvfile.write(f';Baixa;10% a 25%;{format_decimal_br(p10, 2)} a {format_decimal_br(p25, 2)}\n')
                csvfile.write(f';Média;25% a 75%;{format_decimal_br(p25, 2)} a {format_decimal_br(p75, 2)}\n')
                csvfile.write(f';Alta;75% a 90%;{format_decimal_br(p75, 2)} a {format_decimal_br(p90, 2)}\n')
                csvfile.write(f';Muito Alta;90% a 100%;≥ {format_decimal_br(p90, 2)}\n')
                
                csvfile.write('\n')
            
            # Escreve estatísticas para cada variável
            if tempos_merge:
                escrever_estatisticas(csvfile, "Tempo até Merge", tempos_merge, "horas")
            
            if arquivos_alterados:
                escrever_estatisticas(csvfile, "Arquivos Alterados", arquivos_alterados, "arquivos")
            
            if linhas_modificadas:
                escrever_estatisticas(csvfile, "Linhas Modificadas", linhas_modificadas, "linhas")
            
            # 6. INFORMAÇÕES METODOLÓGICAS
            csvfile.write(';' * 5 + ' INFORMAÇÕES METODOLÓGICAS ' + ';' * 5 + '\n')
            csvfile.write(';--- FÓRMULAS UTILIZADAS ---\n')
            csvfile.write(';Média aritmética (Triola, 2024);μ = Σ(xi) / n\n')
            csvfile.write(';Desvio padrão amostral;s = √[Σ(xi - μ)² / (n-1)]\n')
            csvfile.write(';Amplitude Interquartil;AIQ = Q3 - Q1\n')
            csvfile.write(';Limites de Tukey (1977);LI = Q1 - 1,5×AIQ / LS = Q3 + 1,5×AIQ\n')
            csvfile.write(';Método de percentis;Hyndman e Fan (1996), p = (i-1)/(n-1)\n')
            csvfile.write(';Coeficiente de variação;CV = (s/μ) × 100%\n')
            csvfile.write('\n')
            
            # 7. INTERPRETAÇÃO DOS RESULTADOS
            csvfile.write(';' * 5 + ' INTERPRETAÇÃO DOS RESULTADOS ' + ';' * 5 + '\n')
            csvfile.write(';--- ORIENTAÇÕES PARA ANÁLISE ---\n')
            csvfile.write(';1. Média e Mediana;Compare estes valores. Se média > mediana, há assimetria positiva\n')
            csvfile.write(';2. Desvio Padrão;Quanto maior, maior a dispersão dos dados em relação à média\n')
            csvfile.write(';3. Coeficiente de Variação;CV < 15%: baixa variabilidade; 15-30%: média; >30%: alta\n')
            csvfile.write(';4. Outliers;Valores além dos limites de Tukey podem indicar casos atípicos\n')
            csvfile.write(';5. AIQ;Representa a faixa onde está concentrada a metade central dos dados\n')
            csvfile.write(';6. Classificação;Use os percentis para categorizar novos PRs em termos de complexidade\n')
            csvfile.write('\n')
    
    print(f"  -> Gerado: {save_path+output_file} ({len(prs)} PRs)")
    print(f"  -> Incluída análise estatística descritiva")
    
    # Informação adicional sobre formato
    print(f"  Nota: 'time_to_merge_hours' está em formato DECIMAL brasileiro (ex: 12,5 horas)")
    print(f"  Nota: Todos os números no padrão brasileiro (vírgula decimal, sem separador de milhar)")
    
    return save_path+output_file

# ==============================================
# FUNÇÃO PRINCIPAL
# ==============================================

def main():
    """Função principal"""
    print("=" * 60)
    print("CONVERSOR JSON PARA CSV - VERSÃO COM ANÁLISE ESTATÍSTICA")
    print("FORMATO BRASILEIRO: vírgula decimal, sem separador de milhar")
    print("=" * 60)
    print("Novas funcionalidades:")
    print("1. time_to_merge_hours em formato DECIMAL brasileiro (ex: 12,5)")
    print("2. Coluna 'cross_modules' com todos os módulos do PR")
    print("3. Coluna 'commit_messages' com todas as mensagens")
    print("4. Análise estatística descritiva incluída no final do CSV")
    print("5. Classificação por percentis (Hyndman e Fan, 1996)")
    print("6. Identificação de outliers (Tukey, 1977)")
    print("-" * 60)
    
    # Procura automaticamente todos os arquivos github_data_*.json
    json_files = glob.glob("data/raw/github_data_*.json")
    
    if not json_files:
        print("Nenhum arquivo 'github_data_*.json' encontrado.")
        print("Diretório atual:", os.getcwd())
        return
    
    print(f"\nEncontrados {len(json_files)} arquivo(s):")
    for file in json_files:
        file_size = os.path.getsize(file) / 1024
        file_size_br = format_decimal_br(file_size, 1)
        print(f"  - {os.path.basename(file)} ({file_size_br} KB)")
    
    # Processa cada arquivo
    print(f"\nProcessando arquivos...")
    csv_files = []
    
    for json_file in json_files:
        csv_file = process_json_file(json_file)
        if csv_file:
            csv_files.append(csv_file)
    
    # Resumo
    print(f"\n" + "=" * 60)
    if csv_files:
        print("CONVERSÃO E ANÁLISE CONCLUÍDAS!")
        print(f"Arquivos CSV gerados: {len(csv_files)}")
        print("\nSEÇÕES INCLUÍDAS NOS CSVs:")
        print("1. Dados dos Pull Requests (PRs)")
        print("2. Análise estatística descritiva completa")
        print("3. Informações metodológicas")
        print("4. Interpretação dos resultados")
        
        # Dicas para Google Sheets
        print(f"\nDICAS PARA IMPORTAR NO GOOGLE SHEETS:")
        print("1. Vá em Arquivo > Importar")
        print("2. Selecione o arquivo CSV")
        print("3. Escolha 'Separar tipo' e selecione 'Ponto-e-vírgula'")
        print("4. As colunas numéricas já estarão no formato brasileiro")
        print("5. A análise estatística está nas últimas linhas do arquivo")
        
        print(f"\nANÁLISES DISPONÍVEIS:")
        print("• Estatísticas descritivas básicas")
        print("• Medidas de dispersão")
        print("• Quartis e percentis")
        print("• Identificação de outliers (Tukey)")
        print("• Classificação por complexidade")
        
        print(f"\nArquivos gerados:")
        for csv_file in csv_files:
            if os.path.exists(csv_file):
                size = os.path.getsize(csv_file) / 1024
                size_br = format_decimal_br(size, 1)
                print(f"  - {csv_file} ({size_br} KB)")
    else:
        print("Nenhum arquivo convertido.")

# ==============================================
# EXECUÇÃO
# ==============================================

if __name__ == "__main__":
    # Configura encoding para evitar problemas no Windows
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    
    main()