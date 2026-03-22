"""
Funções estatísticas para análise quantitativa de dados de Pull Requests
Baseado nas fórmulas descritas:
1. Média aritmética (Triola, 2024)
2. Desvio padrão amostral
3. Amplitude Interquartil (AIQ)
4. Critério de Tukey (1977) para outliers
5. Método de percentis de Hyndman e Fan (1996)
"""

import math
from typing import List, Tuple, Dict

# ==============================================
# FUNÇÕES ESTATÍSTICAS (conforme fórmulas)
# ==============================================

def calcular_media_aritmetica(dados: List[float]) -> float:
    """
    Calcula a média aritmética conforme eq. (1) de Triola (2024)
    μ = Σ(xi) / n
    """
    if not dados:
        return 0.0
    
    n = len(dados)
    soma = sum(dados)
    media = soma / n
    return media

def calcular_desvio_padrao_amostral(dados: List[float]) -> float:
    """
    Calcula o desvio padrão amostral conforme eq. (2)
    s = sqrt( Σ(xi - μ)² / (n-1) )
    """
    if not dados:
        return 0.0
    
    if len(dados) < 2:
        return 0.0
    
    n = len(dados)
    media = calcular_media_aritmetica(dados)
    
    # Calcula a soma dos quadrados das diferenças
    soma_quadrados = sum((x - media) ** 2 for x in dados)
    
    # Desvio padrão amostral (usa n-1 no denominador)
    variancia = soma_quadrados / (n - 1)
    desvio_padrao = math.sqrt(variancia)
    
    return desvio_padrao

def calcular_amplitude_interquartil(dados: List[float]) -> float:
    """
    Calcula a Amplitude Interquartil (AIQ) conforme eq. (3)
    AIQ = Q3 - Q1
    """
    if not dados:
        return 0.0
    
    dados_ordenados = sorted(dados)
    n = len(dados_ordenados)
    
    # Calcula Q1 (percentil 25)
    q1_pos = (n + 1) * 0.25
    q1 = _calcular_percentil_linear(dados_ordenados, q1_pos)
    
    # Calcula Q3 (percentil 75)
    q3_pos = (n + 1) * 0.75
    q3 = _calcular_percentil_linear(dados_ordenados, q3_pos)
    
    aiq = q3 - q1
    return aiq

def _calcular_percentil_linear(dados_ordenados: List[float], posicao: float) -> float:
    """
    Calcula percentil usando interpolação linear (método de Hyndman e Fan)
    """
    n = len(dados_ordenados)
    
    # Se a posição é inteira, retorna o valor correspondente
    if posicao.is_integer() and 1 <= posicao <= n:
        return dados_ordenados[int(posicao) - 1]
    
    # Caso contrário, faz interpolação linear
    k = int(math.floor(posicao)) - 1  # Índice base (0-based)
    d = posicao - math.floor(posicao)  # Parte fracionária
    
    # Garante que os índices estão dentro dos limites
    if k < 0:
        return dados_ordenados[0]
    elif k >= n - 1:
        return dados_ordenados[-1]
    
    # Interpolação linear entre dois valores adjacentes
    valor_k = dados_ordenados[k]
    valor_k1 = dados_ordenados[k + 1]
    
    return valor_k + d * (valor_k1 - valor_k)

def identificar_outliers_tukey(dados: List[float]) -> Tuple[List[float], Dict]:
    """
    Identifica outliers usando o critério de Tukey (1977) conforme eqs. (4) e (5)
    Limite inferior = Q1 - 1.5 * AIQ
    Limite superior = Q3 + 1.5 * AIQ
    """
    if not dados:
        return [], {}
    
    dados_ordenados = sorted(dados)
    n = len(dados_ordenados)
    
    # Calcula Q1 e Q3
    q1_pos = (n + 1) * 0.25
    q1 = _calcular_percentil_linear(dados_ordenados, q1_pos)
    
    q3_pos = (n + 1) * 0.75
    q3 = _calcular_percentil_linear(dados_ordenados, q3_pos)
    
    # Calcula AIQ
    aiq = q3 - q1
    
    # Calcula limites de Tukey
    limite_inferior = q1 - 1.5 * aiq
    limite_superior = q3 + 1.5 * aiq
    
    # Identifica outliers
    outliers = [x for x in dados if x < limite_inferior or x > limite_superior]
    
    # Estatísticas retornadas
    limites = {
        'limite_inferior': limite_inferior,
        'limite_superior': limite_superior,
        'q1': q1,
        'q3': q3,
        'aiq': aiq,
        'contagem_outliers': len(outliers),
        'percentual_outliers': (len(outliers) / n) * 100 if n > 0 else 0
    }
    
    return outliers, limites

def calcular_percentis_hyndman_fan(dados: List[float], percentis: List[float] = None) -> List[float]:
    """
    Calcula percentis usando o método de Hyndman e Fan (1996) conforme eq. (6)
    p = (i - 1) / (n - 1)
    """
    if not dados:
        return []
    
    if percentis is None:
        percentis = [25, 50, 75]
    
    dados_ordenados = sorted(dados)
    n = len(dados_ordenados)
    
    resultados = []
    
    for p in percentis:
        # Converte percentil para proporção (0-1)
        p_decimal = p / 100
        
        # Calcula posição usando fórmula p = (i - 1) / (n - 1)
        # Rearranjando: i = p * (n - 1) + 1
        posicao = p_decimal * (n - 1) + 1
        
        # Calcula valor usando interpolação linear
        valor = _calcular_percentil_linear(dados_ordenados, posicao)
        resultados.append(valor)
    
    return resultados

def resumo_estatistico_completo(dados: List[float]) -> Dict:
    """
    Gera um resumo estatístico completo dos dados
    """
    if not dados:
        return {}
    
    # Estatísticas básicas
    dados_ordenados = sorted(dados)
    n = len(dados)
    media = calcular_media_aritmetica(dados)
    desvio_padrao = calcular_desvio_padrao_amostral(dados)
    aiq = calcular_amplitude_interquartil(dados)
    
    # Calcula quartis
    q1_pos = (n + 1) * 0.25
    q1 = _calcular_percentil_linear(dados_ordenados, q1_pos)
    
    q3_pos = (n + 1) * 0.75
    q3 = _calcular_percentil_linear(dados_ordenados, q3_pos)
    
    mediana_pos = (n + 1) * 0.5
    mediana = _calcular_percentil_linear(dados_ordenados, mediana_pos)
    
    # Outliers
    outliers, limites_tukey = identificar_outliers_tukey(dados)
    
    # Percentis adicionais
    percentis = calcular_percentis_hyndman_fan(dados, [10, 25, 50, 75, 90])
    
    # Coeficiente de variação
    coef_variacao = (desvio_padrao / media) * 100 if media != 0 else 0.0
    
    resumo = {
        'contagem': n,
        'minimo': min(dados),
        'maximo': max(dados),
        'amplitude_total': max(dados) - min(dados),
        'media': media,
        'mediana': mediana,
        'desvio_padrao': desvio_padrao,
        'variancia': desvio_padrao ** 2,
        'coeficiente_variacao': coef_variacao,
        'percentil_10': percentis[0] if len(percentis) > 0 else 0,
        'percentil_25': q1,
        'percentil_75': q3,
        'percentil_90': percentis[4] if len(percentis) > 4 else 0,
        'amplitude_interquartil': aiq,
        'limite_inferior_tukey': limites_tukey.get('limite_inferior', 0),
        'limite_superior_tukey': limites_tukey.get('limite_superior', 0),
        'contagem_outliers': limites_tukey.get('contagem_outliers', 0),
        'percentual_outliers': limites_tukey.get('percentual_outliers', 0)
    }
    
    return resumo