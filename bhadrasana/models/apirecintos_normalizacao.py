"""Normalização de texto dos eventos da API Recintos antes de gravar no banco.

As tabelas apirecintos_* estão em latin1 (que no MySQL é cp1252) e a API manda UTF-8. Caracteres
fora do charset dão erro MySQL 1366 e derrubam o lote inteiro. Além disso, OCR e teclados trocam
letras latinas por homóglifos de outros alfabetos (М cirílico no lugar de M), lixo que nenhum
charset resolve.

Regras do desenho (ver EventoAPIBase.normaliza_textos, que aplica isto a todas as colunas):
- cirúrgico: só caracteres que falham no charset (ou são homóglifos) são tocados; acentos do
  português e todo o resto ficam intactos. Normalizar tudo com NFKC estragaria dado bom
  ('Nº' -> 'No', e 'µ' viraria o mi grego, fora do latin1);
- tabela de confusáveis VISUAL, não fonética: o OCR viu um H, não um N. Letra só vira letra;
- homóglifo é qualidade de dado e fica sempre ligado; representabilidade depende de CHARSET_BANCO
  e pode ser desligada quando as tabelas migrarem para utf8mb4;
- toda troca é devolvida para registro em RegistroRejeitado, que mostra na prática quais
  caracteres aparecem e orienta o crescimento da tabela.

Módulo puro (sem SQLAlchemy), testado em tests/test_apirecintos_normalizacao.py.
"""
import re
import unicodedata
from typing import List, Optional, Tuple

# Charset das tabelas no MySQL. 'latin1' do MySQL == cp1252 do Python. None desliga o teste de
# representabilidade (só homóglifos continuam sendo corrigidos).
CHARSET_BANCO: Optional[str] = 'cp1252'

# Substituto final para caractere sem equivalente. Em coluna de identidade (placa, contêiner) faz
# o validador rejeitar o evento; em coluna auxiliar faz anular o campo. Em texto livre é a marca.
SUBSTITUTO = '?'

# Confusáveis visuais: caractere fora do charset -> equivalente latino/ASCII com a mesma aparência.
# Subconjunto do UTS 39 (confusables.txt) restrito ao que OCR e teclado produzem em placas,
# contêineres e nomes. Letra nunca vira dígito (O cirílico fica O, nunca 0). Todas as chaves são
# não representáveis em cp1252 (há teste garantindo), o que permite o caminho rápido em
# normaliza_texto. Crescer a tabela a partir do que apirecintos_registros_rejeitados mostrar.
HOMOGLIFOS = {
    # Cirílico, maiúsculas
    'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H',
    'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X',
    'Ѕ': 'S', 'І': 'I', 'Ј': 'J', 'Ү': 'Y', 'Ӏ': 'I', 'Ԛ': 'Q',
    'Ԝ': 'W', 'Ё': 'E',
    # Cirílico, minúsculas
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y',
    'х': 'x', 'ѕ': 's', 'і': 'i', 'ј': 'j', 'ԁ': 'd', 'ԛ': 'q',
    'ԝ': 'w', 'һ': 'h', 'ё': 'e',
    # Grego, maiúsculas
    'Α': 'A', 'Β': 'B', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'H', 'Ι': 'I',
    'Κ': 'K', 'Μ': 'M', 'Ν': 'N', 'Ο': 'O', 'Ρ': 'P', 'Τ': 'T',
    'Υ': 'Y', 'Χ': 'X',
    # Grego, minúsculas
    'ο': 'o', 'ν': 'v',
    # Latino estendido sem decomposição canônica (NFKD não resolve)
    'Ł': 'L', 'ł': 'l', 'Đ': 'D', 'đ': 'd', 'Ħ': 'H', 'ħ': 'h',
    'Ŧ': 'T', 'ŧ': 't', 'ı': 'i',
    # Hífens e sinal de menos fora do cp1252
    '‐': '-', '‑': '-', '‒': '-', '−': '-',
}

REGEX_HOMOGLIFOS = re.compile('[%s]' % ''.join(re.escape(c) for c in HOMOGLIFOS))

# Categorias Unicode removidas quando não representáveis: formato (ex.: largura zero U+200B),
# controle e marcas combinantes soltas.
CATEGORIAS_REMOVIVEIS = ('Cf', 'Cc', 'Mn')


def e_representavel(texto: str) -> bool:
    """True se o texto cabe no charset do banco (ou se CHARSET_BANCO é None)."""
    if CHARSET_BANCO is None:
        return True
    try:
        texto.encode(CHARSET_BANCO)
        return True
    except UnicodeEncodeError:
        return False


def normaliza_caractere(c: str) -> str:
    """Escada de normalização para UM caractere não representável. '' significa remover.

    1. homóglifo visual; 2. equivalente de compatibilidade (NFKC: largura total, ligaduras);
    3. letra base sem acento (NFKD sem marcas combinantes); 4. invisíveis removidos; 5. SUBSTITUTO.
    """
    if c in HOMOGLIFOS:
        return HOMOGLIFOS[c]
    compat = unicodedata.normalize('NFKC', c)
    if compat != c and e_representavel(compat):
        return compat
    base = ''.join(HOMOGLIFOS.get(ch, ch) for ch in unicodedata.normalize('NFKD', c)
                   if unicodedata.category(ch) != 'Mn')
    if base and base != c and e_representavel(base):
        return base
    if unicodedata.category(c) in CATEGORIAS_REMOVIVEIS:
        return ''
    return SUBSTITUTO


def normaliza_texto(texto: str) -> Tuple[str, List[Tuple[str, str]]]:
    """Normaliza um texto para o charset do banco, caractere a caractere e só onde for preciso.

    Returns: (texto_normalizado, substituicoes), com substituicoes = lista de (original, novo) na
    ordem de ocorrência, sem repetir pares. Lista vazia: texto devolvido igual ao recebido.
    """
    if not isinstance(texto, str) or not texto:
        return texto, []
    # Caminho rápido (quase todos os textos): nada a fazer
    if e_representavel(texto) and not REGEX_HOMOGLIFOS.search(texto):
        return texto, []
    saida = []
    substituicoes = {}
    for c in texto:
        if c in HOMOGLIFOS:
            novo = HOMOGLIFOS[c]
        elif e_representavel(c):
            novo = c
        else:
            novo = normaliza_caractere(c)
        if novo != c:
            substituicoes[(c, novo)] = None
        saida.append(novo)
    return ''.join(saida), list(substituicoes)


def _escape(c: str) -> str:
    codigo = ord(c)
    return '\\u%04x' % codigo if codigo <= 0xFFFF else '\\U%08x' % codigo


def escapa_nao_representaveis(texto: str) -> str:
    """Troca só os caracteres fora do charset por escape ASCII ('\\u041c'), preservando os demais.

    Usado para gravar a evidência (valor original) em tabela latin1 sem perder o código do
    caractere. A própria tabela de rejeição nunca pode falhar por charset.
    """
    if not isinstance(texto, str) or e_representavel(texto):
        return texto
    return ''.join(c if e_representavel(c) else _escape(c) for c in texto)


def descreve_substituicoes(substituicoes: List[Tuple[str, str]]) -> str:
    """Descrição segura para o charset das trocas feitas, para o detalhe de RegistroRejeitado.

    Ex.: '\\u041c -> M; \\u200b removido; \\u6c49 -> ?'
    """
    partes = []
    for original, novo in substituicoes:
        original_esc = escapa_nao_representaveis(original)
        partes.append(f'{original_esc} removido' if novo == '' else f'{original_esc} -> {novo}')
    return '; '.join(partes)
