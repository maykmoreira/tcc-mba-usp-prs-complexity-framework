#!/usr/bin/env python3
"""
Coletor de Dados do GitHub GraphQL para Análise de Pull Requests
Autor: Mayk Moreira
Data: 2025
"""

import requests
import json
import time
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

class GitHubDataCollector:
    """Classe para coleta de dados de Pull Requests via GitHub GraphQL API"""
    
    def __init__(self, token: str):
        """
        Inicializa o coletor com token de autenticação
        
        Args:
            token: GitHub Personal Access Token
        """
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "TCC-Analysis-Tool/1.0"
        }
        self.base_url = "https://api.github.com/graphql"
        
    def safe_print(self, message: str):
        """
        Imprime mensagens de forma segura, lidando com problemas de codificação no Windows
        
        Args:
            message: Mensagem a ser impressa
        """
        try:
            print(message)
        except UnicodeEncodeError:
            replacements = {
                "📄": "[ARQUIVO]",
                "✅": "[OK]",
                "💾": "[SALVO]",
                "🎯": "[ALVO]",
                "⚠️": "[ATENCAO]",
                "🔍": "[BUSCA]",
                "📊": "[DADOS]",
                "🚫": "[ERRO]",
                "🔑": "[CHAVE]",
                "┌": "+",
                "├": "+",
                "└": "+",
                "─": "-",
                "│": "|"
            }
            
            clean_message = message
            for emoji, replacement in replacements.items():
                clean_message = clean_message.replace(emoji, replacement)
            
            try:
                print(clean_message)
            except:
                ascii_message = message.encode('ascii', 'ignore').decode('ascii')
                print(ascii_message)
    
    def load_query(self, query_file: str = "scripts/query.graphql") -> str:
        """
        Carrega a query GraphQL de um arquivo
        
        Args:
            query_file: Caminho para o arquivo com a query
            
        Returns:
            String com a query GraphQL
        """
        try:
            with open(query_file, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            self.safe_print(f"Erro: Arquivo '{query_file}' não encontrado.")
            self.safe_print("Certifique-se de que o arquivo query.graphql está no mesmo diretório.")
            exit(1)
    
    def execute_query(self, query: str, variables: Dict) -> Dict:
        """
        Executa uma query GraphQL na API do GitHub
        
        Args:
            query: Query GraphQL
            variables: Variáveis para a query
            
        Returns:
            Resposta JSON da API
        """
        payload = {
            "query": query,
            "variables": variables
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                self.safe_print("Erro 401: Token de autenticação inválido.")
                self.safe_print("Verifique se seu GitHub PAT está correto e tem permissões suficientes.")
                exit(1)
            elif response.status_code == 403:
                self.safe_print("Erro 403: Limite de requisições excedido ou permissões insuficientes.")
                # Verifica os headers de rate limit
                if 'X-RateLimit-Remaining' in response.headers:
                    remaining = response.headers['X-RateLimit-Remaining']
                    reset_time = response.headers.get('X-RateLimit-Reset', '')
                    if reset_time:
                        reset_dt = datetime.fromtimestamp(int(reset_time))
                        self.safe_print(f"   Limite restante: {remaining}")
                        self.safe_print(f"   Reset em: {reset_dt}")
                exit(1)
            else:
                self.safe_print(f"Erro HTTP {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.safe_print(f"Erro de conexão: {e}")
            return None
    
    def collect_repository_data(self, owner: str, repo: str, max_prs: int = 100) -> Dict:
        """
        Coleta dados completos de um repositório incluindo README e PRs
        
        Args:
            owner: Proprietário do repositório (ex: 'spring-projects')
            repo: Nome do repositório (ex: 'spring-framework')
            max_prs: Número máximo de PRs a coletar
            
        Returns:
            Dicionário com README e lista de PRs
        """
        self.safe_print(f"Coletando dados do repositório: {owner}/{repo}")
        self.safe_print(f"Meta: {max_prs} Pull Requests mergeados")
        
        query = self.load_query()
        all_data = {
            "metadata": {
                "repository": f"{owner}/{repo}",
                "collected_at": datetime.now().isoformat(),
                "query_parameters": {
                    "owner": owner,
                    "name": repo,
                    "max_prs": max_prs
                }
            },
            "readme": None,
            "pull_requests": []
        }
        
        # Variáveis para paginação
        has_next_page = True
        end_cursor = None
        prs_collected = 0
        batch_size = 30  # GitHub permite até 100 por página
        
        while has_next_page and prs_collected < max_prs:
            self.safe_print(f"Página: {prs_collected // batch_size + 1} - Coletados: {prs_collected}/{max_prs}")
            
            variables = {
                "owner": owner,
                "name": repo,
                "first": min(batch_size, max_prs - prs_collected),
                "after": end_cursor
            }
            
            result = self.execute_query(query, variables)
            
            if not result:
                self.safe_print("Falha na execução da query. Interrompendo.")
                break
            
            # Verifica erros na resposta GraphQL
            if "errors" in result:
                self.safe_print("Erros na query GraphQL:")
                for error in result["errors"]:
                    self.safe_print(f"   - {error.get('message', 'Erro desconhecido')}")
                break
            
            data = result.get("data", {}).get("repository", {})
            
            # Armazena README apenas na primeira página
            if prs_collected == 0:
                all_data["readme"] = data.get("object", {}).get("text", "")
                self.safe_print("[OK] README coletado com sucesso")
            
            # Processa PRs da página atual
            prs_data = data.get("pullRequests", {})
            prs = prs_data.get("nodes", [])
            
            all_data["pull_requests"].extend(prs)
            prs_collected += len(prs)
            
            # Atualiza informações de paginação
            page_info = prs_data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            end_cursor = page_info.get("endCursor")
            
            # Rate limiting: respeita o limite da API
            time.sleep(1)
            
            # Exibe progresso
            if prs:
                latest_pr = prs[0]
                self.safe_print(f"   + Ultimo PR: #{latest_pr.get('number')} - {latest_pr.get('title')[:50]}...")
                self.safe_print(f"   + Tempo medio estimado restante: {(max_prs - prs_collected) / batch_size * 1.5:.1f}s")
        
        self.safe_print(f"\nColeta concluida!")
        self.safe_print(f"   Total de PRs coletados: {len(all_data['pull_requests'])}")
        
        if all_data['pull_requests']:
            self.safe_print(f"   PR mais recente: #{all_data['pull_requests'][0]['number']}")
            self.safe_print(f"   PR mais antigo: #{all_data['pull_requests'][-1]['number']}")
        else:
            self.safe_print(f"   PR mais recente: N/A")
            self.safe_print(f"   PR mais antigo: N/A")
        
        return all_data
    
    def save_to_file(self, data: Dict, filename: Optional[str] = None) -> str:
        """
        Salva os dados coletados em um arquivo JSON
        
        Args:
            data: Dados a serem salvos
            filename: Nome do arquivo (opcional)
            
        Returns:
            Caminho do arquivo salvo
        """
        save_path = "data/raw/"
        if not filename:
            owner = data["metadata"]["query_parameters"]["owner"]
            repo = data["metadata"]["query_parameters"]["name"]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"github_data_{owner}_{repo}_{timestamp}.json"
        
        with open(save_path+filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        
        self.safe_print(f"[SALVO] Dados salvos em: {save_path+filename}")
        self.safe_print(f"   Tamanho do arquivo: {os.path.getsize(save_path+filename) / 1024:.1f} KB")
        return filename

def main():
    """Função principal do script"""
    print("=" * 60)
    print("COLETOR DE DADOS GITHUB PARA TCC")
    print("=" * 60)
    
    # 1. Configuração do Token
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        print("\n[CHAVE] Token não encontrado nas variáveis de ambiente.")
        print("Por favor, insira seu GitHub Personal Access Token:")
        print("(O token não será exibido na tela)")
        
        import getpass
        token = getpass.getpass("Token: ").strip()
        
        if not token:
            print("Token não fornecido. Encerrando.")
            exit(1)
    
    # 2. Configuração do Repositório
    print("\nConfiguração do Repositório")
    print("   Exemplos:")
    print("   - spring-projects/spring-framework")
    print("   - elastic/elasticsearch")
    print("   - kubernetes/kubernetes")
    
    owner = input("   Proprietario do repositorio (owner): ").strip()
    repo = input("   Nome do repositorio (name): ").strip()
    
    if not owner or not repo:
        print("Proprietario ou repositorio não informado.")
        exit(1)
    
    # 3. Quantidade de PRs
    try:
        max_prs = int(input("   Quantos PRs mergeados coletar? (padrao: 100): ") or "100")
        if max_prs <= 0:
            print("Numero de PRs deve ser maior que zero.")
            exit(1)
    except ValueError:
        print("Numero invalido. Usando padrao: 100")
        max_prs = 100
    
    # 4. Inicializa o coletor
    print("\nIniciando coleta de dados...")
    collector = GitHubDataCollector(token)
    
    # 5. Coleta os dados
    data = collector.collect_repository_data(
        owner=owner,
        repo=repo,
        max_prs=max_prs
    )
    
    # 6. Salva os dados
    if data["pull_requests"]:
        collector.save_to_file(data)
        
        # Estatísticas básicas
        print("\nEstatisticas Preliminares:")
        pr_times = []
        for pr in data["pull_requests"]:
            if pr.get("createdAt") and pr.get("mergedAt"):
                created = datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))
                merged = datetime.fromisoformat(pr["mergedAt"].replace("Z", "+00:00"))
                hours = (merged - created).total_seconds() / 3600
                pr_times.append(hours)
        
        if pr_times:
            avg_time = sum(pr_times) / len(pr_times)
            print(f"   • Tempo medio ate merge: {avg_time:.1f} horas")
            print(f"   • PR mais rapido: {min(pr_times):.1f} horas")
            print(f"   • PR mais lento: {max(pr_times):.1f} horas")
            print(f"   • Total de PRs com tempo calculavel: {len(pr_times)}")
        
        print("\nProximos passos:")
        print("   1. Execute o script 'convert_to_csv.py' para transformar em planilha")
        print("   2. Use o Deepseek/ChatGPT/Claude com o JSON para analise qualitativa")
        print("   3. Consulte o README para contexto do projeto")
    else:
        print("Nenhum PR foi coletado. Verifique o repositorio e as permissoes.")

if __name__ == "__main__":
    # Configuração do encoding para Windows
    if os.name == 'nt':
        try:
            # Tenta configurar o stdout para UTF-8 no Windows
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        except:
            pass
    
    main()