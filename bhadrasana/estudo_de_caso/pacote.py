"""Pacote de estudos de caso para apresentação (23/11/2026).

Monta um ZIP com o que uma IA (ou uma pessoa) precisa para fazer uma apresentação didática de
estudos de caso, no padrão da apresentação de referência (Comércio ilícito e propriedade
intelectual, 2026): para cada caso, um slide com os dados dos documentos (CE Mercante, BL,
contêiner), um com a imagem de escaneamento do contêiner e um com as fotos da verificação física,
as infrações e o resultado.

De onde vêm os casos:

- de uma Ficha (`ficha_id`);
- ou das `quantidade` maiores Operações do Dashboard de Operações (flags "Operação..."), pelo
  valor das colunas Valor TG + Valor Multas da tela, com as Fichas abertas no `ano` ou sem filtro
  (o padrão da tela). "Fichas pendentes" e "Fichas sem operação informada" não são Operações e
  ficam de fora. Cada Operação vira um caso: a Ficha de maior valor dela (a Ficha principal) dá os
  documentos, o escaneamento e as fotos; a Operação dá o contexto (totais, fiscalizados, as outras
  Fichas).

O ZIP::

    SKILL.md                      instruções para a IA montar o PowerPoint
    indice.json                   a origem, o critério e a lista dos casos
    caso_01_ficha_<id>/
        dados.json                os dados do caso, com os textos dos slides já formatados
        resumo.md                 os mesmos dados, para conferência
        escaneamento_<contêiner>.jpg
        fotos/foto_01.jpg ...     miniaturas das fotos da RVF

Só leitura: nada é gravado no banco nem no GridFS.

A imagem de escaneamento é achada pelo contêiner da RVF e pela data (`metadata.numeroinformado` e
`metadata.dataescaneamento`, os únicos campos confiáveis do GridFS das imagens): a mais recente até
o dia da RVF, até `DIAS_ANTES` dias antes; sem nenhuma, a primeira até `DIAS_DEPOIS` dias depois.
Contêiner e data não garantem que é a mesma operação: a regra usada e a distância em dias vão no
dados.json, para conferir antes de apresentar.
"""
import io
import json
import random
import re
import zipfile
from collections import OrderedDict, defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from gridfs import GridFS
from PIL import Image, ImageOps
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import undefer_group

from ajna_commons.flask.log import logger
from bhadrasana.models import operacoes_dashboard as od
from bhadrasana.models.ovr import Enumerado, OVR, TipoResultado
from bhadrasana.models.virasana_manager import get_imagens_container
from bhadrasana.routes.operacoes_dashboard import descreve_periodo
from virasana.integracao.mercante.mercantealchemy import Conhecimento, Item, Manifesto, \
    NCMItem, TIPOS_BL, TIPOS_TRAFEGO

QUANTIDADE_OPERACOES = 5
QUANTIDADE_FOTOS = 10
# as primeiras fotos na ordem da RVF; as demais da amostra são sorteadas entre as restantes
FOTOS_EM_ORDEM = 6
LADO_FOTO = 800                 # px do lado maior da miniatura
LADO_ESCANEAMENTO = 2400        # o escaneamento só é reduzido se passar disso
QUALIDADE_JPEG = 82
DIAS_ANTES = 90
DIAS_DEPOIS = 10
MAXIMO_CONTEINERES = 3
MAXIMO_MERCADORIAS = 12
MAXIMO_ITENS_TG = 50
MAXIMO_OUTRAS_FICHAS = 10
MAXIMO_FISCALIZADOS = 5
TAMANHO_DESCRICAO = 700
TAMANHO_EMBARCADOR = 200

# As tabelas de referência do NAVI-I (portos, países, posições da NCM), lidas se o repositório
# estiver ao lado deste
REFERENCIAS_NAVI_I = (Path(__file__).resolve().parents[3] /
                      'navi-i' / 'src' / 'navi_i' / 'navii' / 'referencias')
ARQUIVO_SKILL = Path(__file__).resolve().parent / 'SKILL.md'

# Frete do CE (M2 do Mercante): cópia de navi-i/src/navi_i/navii/referencias/frete.json (Tabela
# de Moeda SISCOMEX e domínios do layout EDI do Mercante v3.6)
MOEDAS = {'220': 'USD', '790': 'BRL', '978': 'EUR', '165': 'CAD', '470': 'JPY', '540': 'GBP',
          '070': 'SEK'}
MODALIDADES_FRETE = {'HH': 'House to House', 'PP': 'Pier to Pier', 'HP': 'House to Pier',
                     'PH': 'Pier to House'}
RECOLHIMENTOS_FRETE = {'P': 'Prepaid', 'C': 'Collect'}

# TipoResultado (models/ovr.py), para o texto
RESULTADOS = {1: 'Apreensão', 2: 'Perdimento', 3: 'Crédito tributário', 4: 'Sanção', 5: 'DARF',
              6: 'Multa RFB', 7: 'Multa de outro órgão'}


# ---------------------------------------------------------------- formatação

def limpo(valor) -> str:
    return str(valor or '').strip()


def br_numero(valor, casas: int = 2) -> str:
    """1234.5 -> '1.234,50'; None -> ''."""
    if valor is None:
        return ''
    texto = f'{Decimal(str(valor)):,.{casas}f}'
    return texto.replace(',', 'X').replace('.', ',').replace('X', '.')


def br_inteiro_ou_decimal(valor) -> str:
    """9720 -> '9.720'; 12.5 -> '12,50'."""
    if valor is None:
        return ''
    valor = Decimal(str(valor))
    return br_numero(valor, 0 if valor == valor.to_integral_value() else 2)


def br_moeda(valor, simbolo: str = 'R$') -> str:
    return f'{simbolo} {br_numero(valor or 0)}'


def br_data(valor) -> str:
    return valor.strftime('%d/%m/%Y') if isinstance(valor, (date, datetime)) else ''


def br_data_hora(valor) -> str:
    return valor.strftime('%d/%m/%Y %H:%M') if isinstance(valor, datetime) else br_data(valor)


def formata_documento(documento: Optional[str]) -> str:
    """CNPJ (14 dígitos) e CPF (11) com a máscara; o resto como veio."""
    digitos = od.so_digitos(documento)
    if len(digitos) == 14:
        return f'{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}'
    if len(digitos) == 11:
        return f'{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}'
    return limpo(documento)


def formata_ncm(ncm: Optional[str]) -> str:
    """'66019100' -> '6601.91.00'; outro tamanho, como veio."""
    digitos = od.so_digitos(ncm)
    if len(digitos) == 8:
        return f'{digitos[:4]}.{digitos[4:6]}.{digitos[6:]}'
    return limpo(ncm)


def numero_do_texto(texto) -> Optional[Decimal]:
    """O número de um campo texto do Mercante ('20494.650', '20494,65', '1.234,56'); None se não
    for número."""
    texto = limpo(texto)
    if not texto:
        return None
    if ',' in texto and '.' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    else:
        texto = texto.replace(',', '.')
    try:
        return Decimal(texto)
    except InvalidOperation:
        return None


def data_do_texto(texto) -> str:
    """A data de um campo texto do Mercante em dd/mm/aaaa; formato desconhecido, como veio."""
    texto = limpo(texto)
    for formato in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y', '%Y%m%d', '%d%m%Y'):
        try:
            return datetime.strptime(texto, formato).strftime('%d/%m/%Y')
        except ValueError:
            continue
    return texto


def rotulo(funcao: Callable, valor) -> str:
    """O texto de um código de `Enumerado` (fase, tipo de operação, unidade); sem código, ''."""
    if valor is None:
        return ''
    try:
        return funcao(int(valor))
    except (IndexError, TypeError, ValueError):
        return str(valor)


def corta(texto, tamanho: int) -> str:
    texto = ' '.join(str(texto or '').split())
    return texto if len(texto) <= tamanho else texto[:tamanho - 1].rstrip() + '…'


def junta(*partes, separador: str = ' – ') -> str:
    return separador.join(parte for parte in partes if parte)


def nome_curto(nome: str) -> str:
    """A primeira palavra do nome (como 'POLUS' e 'MENFIS' na apresentação de referência); curta
    demais, as duas primeiras."""
    palavras = re.sub(r'[^\w\s&-]', ' ', nome or '').split()
    if not palavras:
        return ''
    if len(palavras[0]) < 3 and len(palavras) > 1:
        return ' '.join(palavras[:2])
    return palavras[0]


class Referencias:
    """Nomes de portos, países e posições da NCM pelas tabelas do NAVI-I; sem a pasta, só os
    códigos."""

    def __init__(self, pasta=REFERENCIAS_NAVI_I):
        self.pasta = Path(pasta) if pasta else None
        self.disponivel = bool(self.pasta and (self.pasta / 'portos.json').is_file())
        self._tabelas = {}

    def tabela(self, nome: str) -> dict:
        if nome not in self._tabelas:
            caminho = self.pasta / nome if self.disponivel else None
            if caminho and caminho.is_file():
                with open(caminho, encoding='utf-8') as arquivo:
                    self._tabelas[nome] = json.load(arquivo)
            else:
                self._tabelas[nome] = {}
        return self._tabelas[nome]

    def porto(self, codigo: Optional[str]) -> str:
        """'CNNGB' -> 'CNNGB – Ningbo, China'; sem nome conhecido, só o código."""
        codigo = limpo(codigo).upper()
        if not codigo:
            return ''
        porto = self.tabela('portos.json').get(codigo)
        pais = self.tabela('paises.json').get(codigo[:2])
        if porto and pais and porto != pais:     # evita 'Hong Kong, Hong Kong'
            nome = f'{porto}, {pais}'
        else:
            nome = porto or pais or ''
        return f'{codigo} – {nome}' if nome else codigo

    def posicao_ncm(self, ncm: Optional[str]) -> str:
        """A descrição da posição (4 dígitos) da NCM, ou do capítulo; sem tabela, ''."""
        digitos = od.so_digitos(ncm)
        if len(digitos) < 2:
            return ''
        tabela = self.tabela('ncm.json')
        return (tabela.get('posicoes', {}).get(digitos[:4]) or
                tabela.get('capitulos', {}).get(digitos[:2]) or '')


# ---------------------------------------------------------------- escolhas

def escolhe_escaneamento(registros: Iterable[dict], referencia: Optional[datetime],
                         dias_antes: int = DIAS_ANTES,
                         dias_depois: int = DIAS_DEPOIS) -> Optional[dict]:
    """O escaneamento do contêiner para o caso, entre os `registros` do fs.files.

    O mais recente até o dia da `referencia` (a RVF), até `dias_antes` dias antes; sem nenhum, o
    primeiro até `dias_depois` dias depois; fora disso, None. Sem `referencia`, o mais recente.
    Devolve o registro, a data, a regra e os dias da referência ao escaneamento (negativo =
    antes)."""
    datados = [(registro.get('metadata', {}).get('dataescaneamento'), registro)
               for registro in registros]
    datados = [(data, registro) for data, registro in datados if isinstance(data, datetime)]
    if not datados:
        return None
    if referencia is None:
        data, registro = max(datados, key=lambda item: item[0])
        return {'registro': registro, 'data': data, 'dias': None,
                'regra': 'sem data de referência: o escaneamento mais recente do contêiner'}
    fim_do_dia = datetime.combine(referencia.date(), time.max)
    antes = [item for item in datados
             if fim_do_dia - timedelta(days=dias_antes) <= item[0] <= fim_do_dia]
    if antes:
        data, registro = max(antes, key=lambda item: item[0])
        regra = f'o mais recente até o dia da referência (até {dias_antes} dias antes)'
    else:
        depois = [item for item in datados
                  if fim_do_dia < item[0] <= fim_do_dia + timedelta(days=dias_depois)]
        if not depois:
            return None
        data, registro = min(depois, key=lambda item: item[0])
        regra = f'nenhum antes da referência: o primeiro até {dias_depois} dias depois'
    return {'registro': registro, 'data': data, 'regra': regra,
            'dias': (data.date() - referencia.date()).days}


def amostra(itens: Iterable, quantidade: int = QUANTIDADE_FOTOS,
            em_ordem: int = FOTOS_EM_ORDEM, semente: int = 0) -> list:
    """Até `quantidade` itens: os `em_ordem` primeiros e um sorteio entre os demais, na ordem
    original. O sorteio usa a `semente` (o id da Ficha): rodar de novo dá a mesma amostra."""
    itens = list(itens)
    if len(itens) <= quantidade:
        return itens
    em_ordem = max(0, min(em_ordem, quantidade))
    restantes = itens[em_ordem:]
    # não é uso criptográfico: só uma amostra reprodutível de fotos
    sorteio = random.Random(semente)  # nosec B311
    sorteados = set(sorteio.sample(range(len(restantes)), quantidade - em_ordem))
    return itens[:em_ordem] + [item for indice, item in enumerate(restantes)
                               if indice in sorteados]


def reduz_imagem(conteudo: bytes, lado: int, so_se_maior: bool = False) -> bytes:
    """A imagem em JPEG com o lado maior até `lado` px, já girada pela orientação EXIF (fotos de
    celular). `so_se_maior`: a imagem JPEG que já cabe volta como veio (o escaneamento, sem
    recompressão)."""
    with Image.open(io.BytesIO(conteudo)) as original:
        if so_se_maior and max(original.size) <= lado and original.format == 'JPEG':
            return conteudo
        imagem = ImageOps.exif_transpose(original)
        if imagem.mode not in ('RGB', 'L'):
            imagem = imagem.convert('RGB')
        imagem.thumbnail((lado, lado))
        saida = io.BytesIO()
        imagem.save(saida, 'JPEG', quality=QUALIDADE_JPEG, optimize=True)
    return saida.getvalue()


def object_id(valor) -> Optional[ObjectId]:
    try:
        return ObjectId(str(valor))
    except (InvalidId, TypeError):
        return None


def le_arquivo(db, _id) -> Optional[bytes]:
    """O conteúdo de um arquivo do GridFS; None se não existir."""
    oid = object_id(_id)
    if oid is None:
        return None
    fs = GridFS(db)
    return fs.get(oid).read() if fs.exists(oid) else None


# ---------------------------------------------------------------- dados da Ficha e do CE

def valores_da_ficha(ovr: OVR) -> dict:
    """Valor TG, Valor Multas e perdimento, com as regras das colunas do Dashboard de Operações."""
    zero = Decimal('0')
    tgs = sum((tg.valor for tg in ovr.tgs if tg.valor), zero)
    multas = sum((resultado.valor for resultado in ovr.resultados
                  if resultado.valor and
                  resultado.tipo_resultado not in od.TIPOS_FORA_DAS_MULTAS), zero)
    perdimentos = sum((resultado.valor for resultado in ovr.resultados
                       if resultado.valor and
                       resultado.tipo_resultado == TipoResultado.Perdimento.value), zero)
    return {'tg': tgs, 'multas': multas, 'perdimentos': perdimentos, 'total': tgs + multas}


def _consulta_conhecimento(session, ce: str, com_m2: bool):
    consulta = session.query(Conhecimento)
    if com_m2:
        consulta = consulta.options(undefer_group('m2'))
    return consulta.filter(Conhecimento.numeroCEmercante == ce).one_or_none()


def carrega_conhecimento(session, ce: str):
    """O CE do Mercante, com o frete (colunas M2) quando a base já as tem."""
    try:
        return _consulta_conhecimento(session, ce, com_m2=True)
    except SQLAlchemyError as erro:
        logger.warning('Estudo de caso: CE %s sem as colunas do frete (M2): %s', ce, erro)
        session.rollback()
        return _consulta_conhecimento(session, ce, com_m2=False)


def dados_do_frete(conhecimento) -> dict:
    valor = numero_do_texto(getattr(conhecimento, 'valorFrete', None))
    moeda = limpo(getattr(conhecimento, 'codigoMoedaFrete', None))
    moeda = MOEDAS.get(moeda, moeda)
    modalidade = limpo(getattr(conhecimento, 'modalidadeFrete', None)).upper()
    recolhimento = limpo(getattr(conhecimento, 'codigoRecolhimentoFrete', None)).upper()
    return {
        'valor': valor,
        'moeda': moeda,
        'texto': f'{moeda} {br_numero(valor)}'.strip() if valor else '',
        'modalidade': junta(modalidade, MODALIDADES_FRETE.get(modalidade)),
        'recolhimento': RECOLHIMENTOS_FRETE.get(recolhimento, recolhimento),
    }


def dados_do_manifesto(session, numero: str, refs: 'Referencias') -> dict:
    manifesto = None
    if numero:
        manifesto = session.query(Manifesto).filter(Manifesto.numero == numero).one_or_none()
    if manifesto is None:
        return {'numero': numero}
    return {
        'numero': numero,
        'porto_carregamento': refs.porto(manifesto.portoCarregamento),
        'porto_descarregamento': refs.porto(manifesto.portoDescarregamento),
        'viagem': limpo(manifesto.numeroViagem),
        'imo': limpo(manifesto.numeroImoDPC),
        'inicio_operacao': br_data_hora(manifesto.dataInicioOperacaoDate),
    }


def dados_do_conhecimento(session, ce: str, refs: Referencias) -> Optional[dict]:
    """O CE, o manifesto, os contêineres (itens) e as NCMs declaradas no Mercante; None se o CE
    não estiver lá."""
    conhecimento = carrega_conhecimento(session, ce)
    if conhecimento is None:
        return None
    itens = session.query(Item).filter(Item.numeroCEmercante == ce).all()
    ncms = session.query(NCMItem).filter(NCMItem.numeroCEMercante == ce).all()
    consignatario = od.so_digitos(conhecimento.consignatario)
    notify = od.so_digitos(conhecimento.cnpjNotify)
    nomes = od.nomes_das_empresas(session, [consignatario, notify])
    complemento = getattr(conhecimento, 'dadoscomplementaresconsignatario', None)
    tipo_bl = limpo(conhecimento.tipoBLConhecimento)
    tipo_trafego = limpo(conhecimento.tipoTrafego)
    return {
        'ce': ce,
        'ce_master': limpo(conhecimento.numeroCEMaster),
        'bl': limpo(conhecimento.numConhecimento),
        'tipo_bl': TIPOS_BL.get(tipo_bl, tipo_bl),
        'tipo_trafego': TIPOS_TRAFEGO.get(tipo_trafego, tipo_trafego),
        'data_emissao': data_do_texto(conhecimento.dataEmissao),
        'consignatario': {'documento': formata_documento(consignatario),
                          'nome': nomes.get(consignatario, ''),
                          'complemento': limpo(complemento)},
        'notificado': {'documento': formata_documento(notify),
                       'nome': limpo(conhecimento.notify) or nomes.get(notify, '')},
        'embarcador': ' '.join((conhecimento.embarcador or '').split()),
        'porto_origem': refs.porto(conhecimento.portoOrigemCarga),
        'porto_destino_final': refs.porto(conhecimento.portoDestFinal),
        'pais_destino_final': limpo(conhecimento.paisDestinoFinalMercante),
        'descricao': ' '.join((conhecimento.descricao or '').split()),
        'cubagem_m3': numero_do_texto(conhecimento.cubagem),
        'frete': dados_do_frete(conhecimento),
        'manifesto': dados_do_manifesto(session, limpo(conhecimento.manifestoCE), refs),
        'conteineres': [
            {'conteiner': limpo(item.codigoConteiner).upper(), 'tipo_iso': limpo(item.isoCode),
             'lacre': limpo(item.lacre), 'peso_bruto_kg': numero_do_texto(item.pesoBruto),
             'tara_kg': numero_do_texto(item.tara), 'volumes': numero_do_texto(item.qtdeItens)}
            for item in sorted(itens, key=lambda item: (limpo(item.numeroSequencialItemCarga),
                                                        item.ID or 0))
        ],
        'ncms': [
            {'conteiner': limpo(ncm.codigoConteiner).upper(),
             'ncm': formata_ncm(ncm.identificacaoNCM),
             'posicao': refs.posicao_ncm(ncm.identificacaoNCM),
             'descricao': limpo(ncm.descritivo), 'volumes': numero_do_texto(ncm.qtdeVolumes),
             'marca': limpo(ncm.marcaMercadoria)}
            for ncm in sorted(ncms, key=lambda ncm: (limpo(ncm.codigoConteiner),
                                                     limpo(ncm.numeroSequencialItemCarga),
                                                     ncm.ID or 0))
        ],
    }


def ordena_rvfs(rvfs) -> list:
    return sorted(rvfs, key=lambda rvf: (rvf.datahora or rvf.create_date or datetime.min,
                                         rvf.id or 0))


def dados_das_rvfs(rvfs: list) -> List[dict]:
    return [{
        'id': rvf.id,
        'data': br_data_hora(rvf.datahora or rvf.create_date),
        'conteiner': limpo(rvf.numerolote).upper(),
        'ce': limpo(rvf.numeroCEmercante),
        'descricao': limpo(rvf.descricao),
        'peso_kg': rvf.peso,
        'volume_m3': rvf.volume,
        'inspecao_nao_invasiva': bool(rvf.inspecaonaoinvasiva),
        'infracoes': [infracao.nome for infracao in rvf.infracoesencontradas],
        'marcas': [marca.nome for marca in rvf.marcasencontradas],
        'lacres_verificados': [lacre.numero for lacre in rvf.lacresverificados],
        'k9': [k9.nome for k9 in rvf.k9sutilizados],
        'apreensoes': [{'tipo': apreensao.tipo.descricao if apreensao.tipo else '',
                        'descricao': limpo(apreensao.descricao), 'peso_kg': apreensao.peso}
                       for apreensao in rvf.apreensoes],
        'quantidade_fotos': len(rvf.imagens),
    } for rvf in rvfs]


def unidade(codigo) -> str:
    return rotulo(Enumerado.unidadeMedida, codigo).strip()


def dados_dos_tgs(ovr: OVR) -> List[dict]:
    tgs = []
    for tg in sorted(ovr.tgs, key=lambda tg: tg.id or 0):
        itens = sorted(tg.itenstg, key=lambda item: (item.numero or 0, item.id or 0))
        tgs.append({
            'numero': limpo(tg.numerotg),
            'conteiner': limpo(tg.numerolote),
            'descricao': limpo(tg.descricao),
            'tipo_mercadoria': tg.tipomercadoria.nome if tg.tipomercadoria else '',
            'quantidade': tg.qtde,
            'unidade': unidade(tg.unidadedemedida),
            'valor': tg.valor,
            'valor_texto': br_moeda(tg.valor) if tg.valor else '',
            'quantidade_itens': len(itens),
            'itens': [{'descricao': limpo(item.descricao),
                       'marca': item.marca.nome if item.marca else '',
                       'modelo': limpo(item.modelo), 'ncm': formata_ncm(item.ncm),
                       'quantidade': item.qtde, 'unidade': unidade(item.unidadedemedida),
                       'valor': item.valor}
                      for item in itens[:MAXIMO_ITENS_TG]],
        })
    return tgs


def _ordem_de_registro(registro):
    return registro.create_date or datetime.min, registro.id or 0


def dados_da_ficha(session, ovr: OVR) -> dict:
    documento = od.so_digitos(ovr.cnpj_fiscalizado)
    nome = od.nomes_das_empresas(session, [documento]).get(documento, '') if documento else ''
    valores = valores_da_ficha(ovr)
    return {
        'id': ovr.id,
        'numero': ovr.get_numero(),
        'ano': ovr.get_ano(),
        'tipo_operacao': rotulo(Enumerado.tipoOperacao, ovr.tipooperacao),
        'fase': rotulo(Enumerado.faseOVR, ovr.fase),
        'abertura': br_data(ovr.datahora),
        'recinto': ovr.recinto.nome if ovr.recinto else '',
        'setor': limpo(ovr.setor.nome) if ovr.setor else '',
        'ce': limpo(ovr.numeroCEmercante),
        'due': limpo(ovr.numerodeclaracao),
        'fiscalizado': {'documento': formata_documento(documento), 'nome': nome},
        'observacoes': limpo(ovr.observacoes),
        'flags': [flag.nome for flag in ovr.flags],
        'valores': {chave: {'valor': valor, 'texto': br_moeda(valor)}
                    for chave, valor in valores.items()},
        'resultados': [{'tipo': RESULTADOS.get(resultado.tipo_resultado,
                                               str(resultado.tipo_resultado)),
                        'valor': resultado.valor,
                        'valor_texto': br_moeda(resultado.valor) if resultado.valor else '',
                        'registrado_em': br_data(resultado.create_date)}
                       for resultado in sorted(ovr.resultados, key=_ordem_de_registro)],
        'processos': [{'tipo': processo.tipoprocesso.descricao if processo.tipoprocesso else '',
                       'numero': limpo(processo.numero)} for processo in ovr.processos],
        'eventos': [{'data': br_data_hora(evento.create_date),
                     'evento': evento.tipoevento.nome if evento.tipoevento else '',
                     'motivo': corta(evento.motivo, 200)}
                    for evento in sorted(ovr.historico, key=_ordem_de_registro)
                    if not evento.excluido],
    }


# ---------------------------------------------------------------- os slides

def soma(valores) -> Optional[Decimal]:
    valores = [valor for valor in valores if valor is not None]
    return sum(valores, Decimal('0')) if valores else None


def campos_do_conhecimento(ficha: dict, conhecimento: dict) -> list:
    consignatario = conhecimento['consignatario']
    fiscalizado = ficha['fiscalizado']
    importador = consignatario['nome'] or consignatario['complemento']
    campos = [['Importador (consignatário)', importador], ['CNPJ', consignatario['documento']]]
    if fiscalizado['documento'] and \
            od.so_digitos(fiscalizado['documento']) != od.so_digitos(consignatario['documento']):
        campos.append(['Fiscalizado na Ficha', junta(fiscalizado['nome'],
                                                     fiscalizado['documento'])])
    notificado, manifesto = conhecimento['notificado'], conhecimento['manifesto']
    tipo_bl = f"({conhecimento['tipo_bl']})" if conhecimento['tipo_bl'] else ''
    campos += [
        ['Notificado', junta(notificado['nome'], notificado['documento'])],
        ['Exportador (embarcador)', corta(conhecimento['embarcador'], TAMANHO_EMBARCADOR)],
        ['Porto de origem', conhecimento['porto_origem']],
        ['Porto de carregamento', manifesto.get('porto_carregamento')],
        ['Porto de descarregamento', manifesto.get('porto_descarregamento')],
        ['Porto de destino final', conhecimento['porto_destino_final']],
        ['Manifesto', manifesto['numero']],
        ['Conhecimento (BL)', junta(conhecimento['bl'], tipo_bl, separador=' ')],
        ['CE-Mercante', conhecimento['ce']],
        ['CE master', conhecimento['ce_master']],
        ['Data de emissão do BL', conhecimento['data_emissao']],
    ]
    conteineres = conhecimento['conteineres']
    peso = soma(item['peso_bruto_kg'] for item in conteineres)
    cubagem = conhecimento['cubagem_m3']
    frete = conhecimento['frete']
    campos += [
        ['Contêiner', ', '.join(item['conteiner'] for item in conteineres if item['conteiner'])],
        ['Tipo de contêiner (ISO)', ', '.join(sorted({item['tipo_iso'] for item in conteineres
                                                       if item['tipo_iso']}))],
        ['Lacre', ', '.join(item['lacre'] for item in conteineres if item['lacre'])],
        ['Peso bruto declarado', f'{br_numero(peso, 3)} kg' if peso else ''],
        ['Cubagem', f'{br_numero(cubagem, 3)} m³' if cubagem else ''],
        ['Volumes', br_inteiro_ou_decimal(soma(item['volumes'] for item in conhecimento['ncms']))],
        ['Frete', frete['texto']],
        ['Modalidade do frete', frete['modalidade']],
        ['Pagamento do frete', frete['recolhimento']],
        ['Descrição da carga no CE', corta(conhecimento['descricao'], 300)],
    ]
    return campos


def campos_de_abertura(ficha: dict, conhecimento: Optional[dict],
                       operacao: Optional[dict]) -> list:
    """[rótulo, valor] do slide de abertura, na ordem da apresentação de referência; os vazios
    ficam de fora."""
    if conhecimento:
        campos = campos_do_conhecimento(ficha, conhecimento)
    else:
        campos = [['Fiscalizado', junta(ficha['fiscalizado']['nome'],
                                        ficha['fiscalizado']['documento'])],
                  ['CE-Mercante', ficha['ce']]]
    campos += [
        ['DUE', ficha['due']],
        ['Ficha', junta(str(ficha['id']), f"({ficha['tipo_operacao']})"
                        if ficha['tipo_operacao'] else '', separador=' ')],
        ['Recinto', ficha['recinto']],
        ['Abertura da Ficha', ficha['abertura']],
    ]
    if operacao:
        campos += [['Operação', operacao['nome']],
                   ['Fichas na Operação', str(operacao['fichas'])],
                   ['Valor da Operação (TG + multas)', operacao['valor_total']]]
    return [[rotulo_do_campo, valor] for rotulo_do_campo, valor in campos if valor]


def mercadorias_declaradas(conhecimento: Optional[dict]) -> list:
    """As linhas de mercadoria do CE (NCM, posição, descrição, volumes): itens com a mesma NCM e a
    mesma descrição viram uma linha, com os volumes somados."""
    if not conhecimento:
        return []
    linhas = OrderedDict()
    for ncm in conhecimento['ncms']:
        chave = (ncm['ncm'], ncm['descricao'].upper())
        if chave not in linhas:
            linhas[chave] = {'ncm': ncm['ncm'], 'posicao': ncm['posicao'],
                             'descricao': ncm['descricao'], 'volumes': [], 'marca': ncm['marca']}
        linhas[chave]['volumes'].append(ncm['volumes'])
    for linha in linhas.values():
        linha['volumes'] = br_inteiro_ou_decimal(soma(linha['volumes']))
    return list(linhas.values())


def destaques_do_resultado(ficha: dict, rvfs: list, tgs: list) -> list:
    """Os números do slide de resultado (as 'grandes cifras' da apresentação de referência)."""
    valores = ficha['valores']
    destaques = []
    for chave, rotulo_destaque in (('tg', 'Valor das mercadorias retidas (TG)'),
                                   ('perdimentos', 'Perdimento'),
                                   ('multas', 'Multas e créditos')):
        if valores[chave]['valor']:
            destaques.append([rotulo_destaque, valores[chave]['texto']])
    por_unidade = defaultdict(Decimal)
    for tg in tgs:
        if tg['quantidade']:
            por_unidade[tg['unidade'] or 'unidades'] += Decimal(str(tg['quantidade']))
    if por_unidade:
        quantidades = [f'{br_inteiro_ou_decimal(qtde)} {nome}'
                       for nome, qtde in sorted(por_unidade.items())]
        destaques.append(['Quantidade retida', ' + '.join(quantidades)])
    apreensoes = defaultdict(Decimal)
    for rvf in rvfs:
        for apreensao in rvf['apreensoes']:
            if apreensao['peso_kg']:
                apreensoes[apreensao['tipo'] or 'Apreensão'] += Decimal(str(apreensao['peso_kg']))
    for tipo, peso in sorted(apreensoes.items()):
        destaques.append([f'Apreensão – {tipo}', f'{br_numero(peso)} kg'])
    return destaques


def fatos_para_indicadores(conhecimento: Optional[dict], rvfs: list) -> dict:
    """Fatos objetivos que a IA pode usar para sugerir indicadores de risco (sem tirar conclusão
    por conta própria)."""
    fatos = OrderedDict()
    peso_declarado = None
    if conhecimento:
        ncms = {ncm['ncm'] for ncm in conhecimento['ncms'] if ncm['ncm']}
        fatos['ncms_declaradas'] = len(ncms)
        fatos['posicoes_ncm_declaradas'] = len({od.so_digitos(ncm)[:4] for ncm in ncms})
        fatos['porto_origem'] = conhecimento['porto_origem']
        fatos['tipo_bl'] = conhecimento['tipo_bl'] or ''
        fatos['modalidade_frete'] = conhecimento['frete']['modalidade']
        peso_declarado = soma(item['peso_bruto_kg'] for item in conhecimento['conteineres'])
        fatos['peso_bruto_declarado_kg'] = peso_declarado
    peso_rvf = soma(rvf['peso_kg'] for rvf in rvfs)
    fatos['peso_informado_na_rvf_kg'] = peso_rvf
    if peso_declarado and peso_rvf:
        diferenca = (peso_rvf - peso_declarado) / peso_declarado * 100
        fatos['diferenca_peso_rvf_declarado_pct'] = round(float(diferenca), 1)
    fatos['inspecao_nao_invasiva'] = any(rvf['inspecao_nao_invasiva'] for rvf in rvfs)
    fatos['infracoes'] = sorted({infracao for rvf in rvfs for infracao in rvf['infracoes']})
    return fatos


# ---------------------------------------------------------------- o caso

def conteineres_do_caso(ovr: OVR, rvfs: list, conhecimento: Optional[dict]) -> list:
    """[(contêiner, data de referência, rótulo da referência)]: os das RVFs; sem RVF, os do CE com
    a data da Ficha."""
    vistos = OrderedDict()
    for rvf in rvfs:
        conteiner = re.sub(r'[^A-Z0-9]', '', limpo(rvf.numerolote).upper())
        if conteiner and conteiner not in vistos:
            vistos[conteiner] = (rvf.datahora or rvf.create_date, 'data da RVF')
    if not vistos and conhecimento:
        for item in conhecimento['conteineres']:
            if item['conteiner'] and item['conteiner'] not in vistos:
                vistos[item['conteiner']] = (ovr.datahora, 'data de abertura da Ficha')
    return [(conteiner, data, nome)
            for conteiner, (data, nome) in vistos.items()][:MAXIMO_CONTEINERES]


def escaneamento_do_conteiner(mongodb, conteiner: str, referencia, nome_da_referencia: str,
                              avisos: list) -> Optional[tuple]:
    """(arquivo, conteúdo, dados) do escaneamento do contêiner; sem ele, None e um aviso."""
    registros = get_imagens_container(mongodb, conteiner)
    escolha = escolhe_escaneamento(registros, referencia)
    if escolha is None:
        avisos.append(f'Contêiner {conteiner}: nenhum escaneamento de {DIAS_ANTES} dias antes a '
                      f'{DIAS_DEPOIS} dias depois da {nome_da_referencia} '
                      f'({len(registros)} no total para o contêiner).')
        return None
    conteudo = le_arquivo(mongodb, escolha['registro']['_id'])
    if conteudo is None:
        avisos.append(f'Contêiner {conteiner}: o escaneamento não está no GridFS.')
        return None
    arquivo = f'escaneamento_{conteiner}.jpg'
    data = escolha['data']
    return arquivo, reduz_imagem(conteudo, LADO_ESCANEAMENTO, so_se_maior=True), {
        'arquivo': arquivo,
        'conteiner': conteiner,
        'data': br_data_hora(data),
        'referencia': f'{nome_da_referencia}: {br_data_hora(referencia)}' if referencia else '',
        'dias_da_referencia': escolha['dias'],
        'regra': escolha['regra'],
        'escaneamentos_do_conteiner': len(registros),
        'legenda_sugerida': f'Contêiner {conteiner} – escaneado em {br_data(data)}',
    }


def busca_escaneamentos(mongodb, ovr: OVR, rvfs: list, conhecimento: Optional[dict],
                        avisos: list) -> list:
    """[(arquivo, conteúdo, dados)] do escaneamento de cada contêiner do caso."""
    escolhidos = []
    for conteiner, referencia, nome in conteineres_do_caso(ovr, rvfs, conhecimento):
        try:
            escolhido = escaneamento_do_conteiner(mongodb, conteiner, referencia, nome, avisos)
        except Exception as erro:  # o caso sai sem o escaneamento, mas sai
            logger.error('Estudo de caso: escaneamento de %s: %s', conteiner, erro, exc_info=True)
            avisos.append(f'Contêiner {conteiner}: erro ao buscar o escaneamento '
                          f'({type(erro).__name__}).')
            continue
        if escolhido:
            escolhidos.append(escolhido)
    return escolhidos


def _ordem_da_foto(imagem):
    return imagem.ordem if imagem.ordem is not None else 9999, imagem.id or 0


def busca_fotos(mongo_risco, ovr: OVR, rvfs: list, quantidade: int, avisos: list) -> tuple:
    """([(arquivo, miniatura, dados)], total de fotos da Ficha): a amostra das fotos das RVFs."""
    fotos = [(rvf, imagem) for rvf in rvfs for imagem in sorted(rvf.imagens, key=_ordem_da_foto)]
    oids = [oid for oid in (object_id(imagem.imagem) for _, imagem in fotos) if oid]
    existentes = {str(registro['_id']) for registro in
                  mongo_risco['fs.files'].find({'_id': {'$in': oids}}, {'_id': 1})}
    faltando = [imagem.imagem for _, imagem in fotos
                if str(object_id(imagem.imagem)) not in existentes]
    if faltando:
        avisos.append(f'{len(faltando)} foto(s) das RVFs não estão no GridFS: '
                      f'{", ".join(map(str, faltando[:5]))}')
    fotos = [(rvf, imagem) for rvf, imagem in fotos
             if str(object_id(imagem.imagem)) in existentes]
    escolhidas = []
    for posicao, (rvf, imagem) in enumerate(amostra(fotos, quantidade, semente=ovr.id or 0), 1):
        try:
            miniatura = reduz_imagem(le_arquivo(mongo_risco, imagem.imagem), LADO_FOTO)
        except Exception as erro:  # a foto ilegível sai da amostra; o caso continua
            logger.error('Estudo de caso: foto %s: %s', imagem.imagem, erro, exc_info=True)
            avisos.append(f'Foto {imagem.imagem}: não foi possível ler ({type(erro).__name__}).')
            continue
        arquivo = f'fotos/foto_{posicao:02d}.jpg'
        escolhidas.append((arquivo, miniatura, {
            'arquivo': arquivo, 'rvf': rvf.id, 'conteiner': limpo(rvf.numerolote).upper(),
            'ordem_na_rvf': imagem.ordem, 'legenda': limpo(imagem.descricao),
            'marca': imagem.marca.nome if imagem.marca else '',
        }))
    return escolhidas, len(fotos)


def apelido_do_caso(ficha: dict, conhecimento: Optional[dict], operacao: Optional[dict]) -> str:
    if operacao:
        nome = re.sub(r'^opera[çc][ãa]o\s*', '', operacao['nome'], flags=re.IGNORECASE)
    elif conhecimento and conhecimento['consignatario']['nome']:
        nome = conhecimento['consignatario']['nome']
    else:
        nome = ficha['fiscalizado']['nome']
    return nome_curto(nome)


def slide_de_resultado(titulo: str, ficha: dict, rvfs: list, tgs: list, fotos: list,
                       total_fotos: int) -> dict:
    descricoes = [rvf['descricao'] for rvf in rvfs if rvf['descricao']]
    marcas = {marca for rvf in rvfs for marca in rvf['marcas']}
    marcas |= {item['marca'] for tg in tgs for item in tg['itens'] if item['marca']}
    return {
        'titulo': f'{titulo} – resultado',
        'destaques': destaques_do_resultado(ficha, rvfs, tgs),
        'infracoes': sorted({infracao for rvf in rvfs for infracao in rvf['infracoes']}),
        'marcas': sorted(marcas),
        'mercadorias_retidas': [
            {'descricao': tg['descricao'], 'valor': tg['valor_texto'],
             'quantidade': junta(br_inteiro_ou_decimal(tg['quantidade']), tg['unidade'],
                                 separador=' ')}
            for tg in tgs],
        'descricao_rvf': corta(' | '.join(descricoes), TAMANHO_DESCRICAO),
        'fotos': [dados_da_foto for _, _, dados_da_foto in fotos],
        'fotos_na_ficha': total_fotos,
    }


def monta_caso(session, mongodb, mongo_risco, ovr: OVR, numero: int, refs: Referencias,
               quantidade_fotos: int = QUANTIDADE_FOTOS,
               operacao: Optional[dict] = None) -> tuple:
    """(pasta, dados, [(caminho no ZIP, conteúdo)]) de um caso."""
    avisos = []
    pasta = f'caso_{numero:02d}_ficha_{ovr.id}'
    rvfs = ordena_rvfs(ovr.rvfs)
    ficha = dados_da_ficha(session, ovr)
    ce = ficha['ce'] or next((limpo(rvf.numeroCEmercante) for rvf in rvfs
                              if limpo(rvf.numeroCEmercante)), '')
    conhecimento = dados_do_conhecimento(session, ce, refs) if ce else None
    if ce and conhecimento is None:
        avisos.append(f'CE {ce} não encontrado no Mercante.')
    if not ce:
        avisos.append('A Ficha não tem CE (nem nas RVFs): o slide de abertura sai só com os '
                      'dados da Ficha.')
    if not rvfs:
        avisos.append('A Ficha não tem RVF: sem fotos, infrações nem descrição da verificação.')
    dados_rvfs = dados_das_rvfs(rvfs)
    tgs = dados_dos_tgs(ovr)
    escaneamentos = busca_escaneamentos(mongodb, ovr, rvfs, conhecimento, avisos)
    fotos, total_fotos = busca_fotos(mongo_risco, ovr, rvfs, quantidade_fotos, avisos)

    apelido = apelido_do_caso(ficha, conhecimento, operacao)
    titulo = junta(f'Estudo de caso {numero}', apelido)
    mercadorias = mercadorias_declaradas(conhecimento)
    com_imagem = {dados_da_imagem['conteiner'] for _, _, dados_da_imagem in escaneamentos}
    dados = OrderedDict([
        ('caso', numero),
        ('pasta', pasta),
        ('titulo_sugerido', titulo),
        ('nome_curto', apelido),
        ('origem', 'operacao' if operacao else 'ficha'),
        ('operacao', operacao),
        ('slide_abertura', {
            'titulo': titulo,
            'campos': campos_de_abertura(ficha, conhecimento, operacao),
            'mercadorias': mercadorias[:MAXIMO_MERCADORIAS],
            'mercadorias_total': len(mercadorias),
        }),
        ('slide_escaneamento', {
            'titulo': f'{titulo} – escaneamento',
            'imagens': [dados_da_imagem for _, _, dados_da_imagem in escaneamentos],
            'sem_imagem': [conteiner for conteiner, _, _ in
                           conteineres_do_caso(ovr, rvfs, conhecimento)
                           if conteiner not in com_imagem],
        }),
        ('slide_resultado', slide_de_resultado(titulo, ficha, dados_rvfs, tgs, fotos,
                                               total_fotos)),
        ('fatos', fatos_para_indicadores(conhecimento, dados_rvfs)),
        ('ficha', ficha),
        ('conhecimento', conhecimento),
        ('rvfs', dados_rvfs),
        ('tgs', tgs),
        ('avisos', avisos),
    ])
    arquivos = [(f'{pasta}/{arquivo}', conteudo)
                for arquivo, conteudo, _ in escaneamentos + fotos]
    return pasta, dados, arquivos


# ---------------------------------------------------------------- as Operações

def valor_total(dados_operacao: dict) -> Decimal:
    return dados_operacao['total_tgs'] + dados_operacao['total_multas']


def valor_da_linha(ovr: dict) -> Decimal:
    return ovr['valor_tgs'] + ovr['valor_multas']


def maiores_operacoes(session, inicio: Optional[date] = None, fim: Optional[date] = None,
                      quantidade: int = QUANTIDADE_OPERACOES) -> list:
    """[(Operação, dados do Dashboard)] das `quantidade` Operações de maior Valor TG + Valor
    Multas no período.

    Só as Operações (flags "Operação..."), com valor; as categorias virtuais ficam de fora.
    Empate: mais Fichas, depois o nome."""
    candidatas = []
    for operacao in od.listar_operacoes(session):
        if operacao.id < 0:
            continue
        dados = od.monta_dashboard_operacao(session, operacao.id, inicio, fim)
        if valor_total(dados) > 0:
            candidatas.append((operacao, dados))
    candidatas.sort(key=lambda item: (-valor_total(item[1]), -item[1]['total_ovrs'],
                                      item[0].nome))
    return candidatas[:quantidade]


def ficha_principal(dados_operacao: dict) -> dict:
    """A Ficha de maior Valor TG + Valor Multas da Operação; empate: mais RVFs, depois a de menor
    id."""
    return min(dados_operacao['ovrs'],
               key=lambda ovr: (-valor_da_linha(ovr), -ovr['qtd_rvfs'], ovr['id']))


def resumo_da_operacao(session, operacao, dados: dict, inicio, fim, principal_id: int) -> dict:
    od.acrescenta_fiscalizados(session, dados)
    outras = sorted((ovr for ovr in dados['ovrs'] if ovr['id'] != principal_id),
                    key=lambda ovr: (-valor_da_linha(ovr), ovr['id']))
    return {
        'id': operacao.id,
        'nome': operacao.nome,
        'periodo_de_abertura': descreve_periodo(inicio, fim),
        'fichas': dados['total_ovrs'],
        'fichas_concluidas': dados['total_concluidas'],
        'ces': dados['total_ces'],
        'conteineres': dados['total_containers'],
        'rvfs': dados['total_rvfs'],
        'valor_tg': br_moeda(dados['total_tgs']),
        'valor_multas': br_moeda(dados['total_multas']),
        'valor_perdimentos': br_moeda(dados['total_perdimentos']),
        'valor_total': br_moeda(valor_total(dados)),
        'ficha_principal': principal_id,
        'fiscalizados': [{'documento': formata_documento(fiscalizado['cnpj']),
                          'nome': fiscalizado['nome'], 'fichas': fiscalizado['qtd_fichas']}
                         for fiscalizado in dados['fiscalizados'][:MAXIMO_FISCALIZADOS]],
        'outras_fichas': [{'id': ovr['id'], 'ce': limpo(ovr['numeroCEmercante']),
                           'fiscalizado': (ovr.get('fiscalizado_nome') or
                                           formata_documento(ovr['cnpj_fiscalizado'])),
                           'valor': br_moeda(valor_da_linha(ovr))}
                          for ovr in outras[:MAXIMO_OUTRAS_FICHAS]],
    }


def periodo_do_ano(ano: Optional[int]) -> tuple:
    return (date(ano, 1, 1), date(ano, 12, 31)) if ano else (None, None)


# ---------------------------------------------------------------- o ZIP

def _json_padrao(valor):
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    raise TypeError(f'{type(valor).__name__} não vai para o JSON')


def em_json(dados) -> str:
    return json.dumps(dados, ensure_ascii=False, indent=2, default=_json_padrao)


def _celula(texto) -> str:
    return str(texto or '').replace('|', '/').replace('\n', ' ')


def _markdown_da_operacao(operacao: dict) -> list:
    return [f"**{operacao['nome']}** (abertura das Fichas: {operacao['periodo_de_abertura']}): "
            f"{operacao['fichas']} Fichas, valor (TG + multas) {operacao['valor_total']}. "
            f"Ficha principal: {operacao['ficha_principal']}.", '']


def resumo_em_markdown(dados: dict) -> str:
    """O caso em texto, para conferir o que vai para os slides."""
    abertura = dados['slide_abertura']
    escaneamento = dados['slide_escaneamento']
    resultado = dados['slide_resultado']
    linhas = [f"# {dados['titulo_sugerido']}", '']
    if dados['operacao']:
        linhas += _markdown_da_operacao(dados['operacao'])
    linhas += ['## Slide 1 – documentos', '', '| Campo | Informação |', '|---|---|']
    linhas += [f'| {_celula(campo)} | {_celula(valor)} |' for campo, valor in abertura['campos']]
    if abertura['mercadorias']:
        linhas += ['', f"Mercadorias declaradas ({abertura['mercadorias_total']}):", '',
                   '| NCM | Descrição no CE | Volumes |', '|---|---|---|']
        linhas += [f"| {_celula(item['ncm'])} | {_celula(item['descricao'] or item['posicao'])} "
                   f"| {_celula(item['volumes'])} |" for item in abertura['mercadorias']]
    linhas += ['', '## Slide 2 – escaneamento', '']
    for imagem in escaneamento['imagens']:
        linhas.append(f"- `{imagem['arquivo']}`: {imagem['legenda_sugerida']} ({imagem['regra']}; "
                      f"{imagem['referencia']}; {imagem['dias_da_referencia']} dia(s))")
    for conteiner in escaneamento['sem_imagem']:
        linhas.append(f'- {conteiner}: sem escaneamento no prazo')
    linhas += ['', '## Slide 3 – resultado', '']
    linhas += [f'- **{campo}**: {valor}' for campo, valor in resultado['destaques']]
    if resultado['infracoes']:
        linhas.append(f"- Infrações: {', '.join(resultado['infracoes'])}")
    if resultado['marcas']:
        linhas.append(f"- Marcas: {', '.join(resultado['marcas'])}")
    if resultado['descricao_rvf']:
        linhas += ['', f"Verificação física: {resultado['descricao_rvf']}"]
    linhas += ['', f"Fotos ({len(resultado['fotos'])} de {resultado['fotos_na_ficha']} na "
                   'Ficha):', '']
    linhas += [f"- `{foto['arquivo']}` RVF {foto['rvf']}" +
               (f": {foto['legenda']}" if foto['legenda'] else '')
               for foto in resultado['fotos']]
    if dados['avisos']:
        linhas += ['', '## Avisos', ''] + [f'- {aviso}' for aviso in dados['avisos']]
    return '\n'.join(linhas) + '\n'


def texto_da_skill() -> str:
    return ARQUIVO_SKILL.read_text(encoding='utf-8')


def casos_das_operacoes(session, mongodb, mongo_risco, refs: Referencias, inicio, fim,
                        quantidade: int, quantidade_fotos: int) -> list:
    operacoes = maiores_operacoes(session, inicio, fim, quantidade)
    if not operacoes:
        raise ValueError('Nenhuma Operação com Valor TG ou Valor Multas '
                         f'({descreve_periodo(inicio, fim)}).')
    casos = []
    for numero, (operacao, dados) in enumerate(operacoes, 1):
        principal = ficha_principal(dados)
        ovr = session.query(OVR).filter(OVR.id == principal['id']).one()
        resumo = resumo_da_operacao(session, operacao, dados, inicio, fim, principal['id'])
        casos.append(monta_caso(session, mongodb, mongo_risco, ovr, numero, refs,
                                quantidade_fotos, resumo))
    return casos


def monta_indice(casos: list, origem: dict, refs: Referencias, quantidade_fotos: int,
                 agora: datetime) -> dict:
    return OrderedDict([
        ('gerado_em', br_data_hora(agora)),
        ('origem', origem),
        ('parametros', {'fotos_por_caso': quantidade_fotos, 'fotos_em_ordem': FOTOS_EM_ORDEM,
                        'lado_da_foto_px': LADO_FOTO, 'dias_antes': DIAS_ANTES,
                        'dias_depois': DIAS_DEPOIS, 'nomes_de_portos_e_ncm': refs.disponivel}),
        ('casos', [{'caso': dados['caso'], 'pasta': pasta,
                    'titulo_sugerido': dados['titulo_sugerido'], 'ficha': dados['ficha']['id'],
                    'operacao': dados['operacao']['nome'] if dados['operacao'] else None,
                    'valor': dados['ficha']['valores']['total']['texto'],
                    'escaneamentos': len(dados['slide_escaneamento']['imagens']),
                    'fotos': len(dados['slide_resultado']['fotos']),
                    'avisos': len(dados['avisos'])}
                   for pasta, dados, _ in casos]),
    ])


def grava_zip(destino: Path, indice: dict, casos: list):
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, 'w', compression=zipfile.ZIP_DEFLATED) as arquivo_zip:
        arquivo_zip.writestr('SKILL.md', texto_da_skill())
        arquivo_zip.writestr('indice.json', em_json(indice))
        for pasta, dados, arquivos in casos:
            arquivo_zip.writestr(f'{pasta}/dados.json', em_json(dados))
            arquivo_zip.writestr(f'{pasta}/resumo.md', resumo_em_markdown(dados))
            for caminho, conteudo in arquivos:     # JPEG: já comprimido
                arquivo_zip.writestr(caminho, conteudo, compress_type=zipfile.ZIP_STORED)


def gera_pacote(session, mongodb, mongo_risco, destino, ficha_id: Optional[int] = None,
                ano: Optional[int] = None, quantidade: int = QUANTIDADE_OPERACOES,
                quantidade_fotos: int = QUANTIDADE_FOTOS, referencias=REFERENCIAS_NAVI_I,
                agora: Optional[datetime] = None) -> dict:
    """Grava o ZIP em `destino` e devolve o índice. `ficha_id`: uma Ficha; senão, as maiores
    Operações (no `ano`, ou sem filtro).

    `mongodb`: o banco das imagens de escaneamento; `mongo_risco`: o das fotos do Fichas."""
    if ficha_id and ano:
        raise ValueError('Informe a Ficha ou o ano, não os dois.')
    refs = Referencias(referencias)
    if ficha_id:
        ovr = session.query(OVR).filter(OVR.id == ficha_id).one_or_none()
        if ovr is None:
            raise ValueError(f'Ficha {ficha_id} não encontrada.')
        casos = [monta_caso(session, mongodb, mongo_risco, ovr, 1, refs, quantidade_fotos)]
        origem = {'modo': 'ficha', 'ficha': ficha_id}
    else:
        inicio, fim = periodo_do_ano(ano)
        casos = casos_das_operacoes(session, mongodb, mongo_risco, refs, inicio, fim,
                                    quantidade, quantidade_fotos)
        origem = {'modo': 'operacoes', 'ano': ano,
                  'periodo_de_abertura': descreve_periodo(inicio, fim),
                  'criterio': f'as {quantidade} Operações do Dashboard de Operações de maior '
                              'Valor TG + Valor Multas; em cada uma, a Ficha de maior valor é '
                              'o caso'}
    indice = monta_indice(casos, origem, refs, quantidade_fotos, agora or datetime.now())
    grava_zip(Path(destino), indice, casos)
    return indice


def nome_do_pacote(ficha_id: Optional[int] = None, ano: Optional[int] = None,
                   hoje: Optional[date] = None) -> str:
    if ficha_id:
        alvo = f'ficha_{ficha_id}'
    elif ano:
        alvo = f'operacoes_{ano}'
    else:
        alvo = 'operacoes'
    return f'estudos_de_caso_{alvo}_{hoje or date.today():%Y%m%d}.zip'
