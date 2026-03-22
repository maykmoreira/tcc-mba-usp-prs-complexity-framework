# tcc-mba-usp-prs-complexity-framework
Framework para análise de complexidade de Pull Requests com apoio de IA generativa - TCC MBA USP/ESALQ

# TCC MBA USP - Framework para Análise de Complexidade de Pull Requests

Este repositório contém os artefatos desenvolvidos no Trabalho de Conclusão de Curso (TCC) do MBA em Engenharia de Software da USP/ESALQ.

## Objetivo

Desenvolver e validar um framework metodológico para análise de Pull Requests com apoio de IA generativa, visando identificar padrões de complexidade técnica e gerar indicadores que auxiliem na melhoria de estimativas em metodologias ágeis.

## Estrutura do Repositório
```
├── scripts/
│ ├── github_collector.py # Coleta de dados via GitHub GraphQL API
│ └── convert_to_csv.py # Conversão JSON para CSV
├── data/
│ ├── raw/ # Dados brutos coletados (JSON)
│ └── processed/ # Dados processados (CSV)
├── reports/
│ └── spring-framework_relatorio_deepseek.pdf
├── requirements.txt
├── LICENSE
└── README.md
```

## Como Utilizar

### 1. Configuracao do Ambiente

```
git clone https://github.com/maykmoreira/tcc-mba-usp-prs-complexity-framework.git
```
```
cd tcc-mba-usp-prs-complexity-framework
```
```
pip install -r requirements.txt
```

### 2. Coleta de Dados

```
export GITHUB_TOKEN="seu_token_aqui"
```
```
python scripts/github_collector.py
```

### 3. Conversao para CSV
Ao acionar o script de conversão todos os arquivos presentes no diretório /data/raw são processados, convertidos para csv e salvos em /data/processed
```
python scripts/convert_to_csv.py
```

## Análise Quantitativa com Scripts

- Para os arquivos de PRs extraídos do github os resultados .csv presente no diretório /data/processed já contém os dados estatísticos nas últimas linhas dos arquivos
- Periodo: Por default os scripts trabalham os Ultimos 100 Pull Requests mergeados
- Metricas extraidas: tempo ate merge, arquivos alterados, linhas modificadas, numero de revisoes, modulos afetados

## Analise Qualitativa com IA

Os dados processados foram submetidos a analise por meio de prompts estruturados em modelo de linguagem de grande porte (DeepSeek), gerando relatorio com:

- Perfil do repositorio
- Indicadores quantitativos e percentis
- Padroes de complexidade identificados
- Recomendacoes acionaveis para gestao agil

## Citacao

Este trabalho foi desenvolvido como requisito parcial para obtencao do titulo de MBA em Engenharia de Software pela USP/ESALQ.

Autor: Mayk Henrique dos Santos Moreira
Orientador: Daniele Aparecida Cicillini Pimenta
Ano: 2026

## Licenca

Este projeto esta licenciado sob a licenca Apache 2.0 - consulte o arquivo LICENSE para mais detalhes.

## Links Relacionados

- Repositorio Spring Framework: https://github.com/spring-projects/spring-framework
- Repositorio Elasticsearch: https://github.com/elastic/elasticsearch
- Repositorio Kubernetes: https://github.com/kubernetes/kubernetes
- GitHub GraphQL API: https://docs.github.com/pt/graphql
- DeepSeek AI: https://deepseek.com

---

Para reproducao dos resultados, consulte a secao de metodologia no texto completo do TCC.
