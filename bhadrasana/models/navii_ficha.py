"""
Abertura de Ficha pelo NAVI-I: o TRATAMENTO do risco apurado na análise de risco na importação.

A tela NAVI-I fica no repo virasana; plano aprovado pelo usuário em 17/10/2026
(virasana/navii/CONTEXTO.md, "Tratamento do risco: Fichas pelo NAVI-I"). Chamado pelo NAVI-I,
não por rota do Fichas.

Só ADITIVO: não muda nenhuma regra do Fichas. Usa os models e as regras existentes (usuário
habilitado, fase, responsável, eventos pelo `EventoEspecial` via `gera_eventoovr`) e grava TUDO
numa transação:
  - Ficha de "Repressão mediante análise de risco na importação" (`tipooperacao = 1`): CE,
    setor do analista, recinto onde o contêiner está, CNPJ do consignatário, observações
    "[NAVI-I] ..." (resumo do risco, até TAMANHO_RESUMO caracteres; se faltar espaço, o campo
    será ampliado) e a flag NAVI-I; o analista fica como responsável (evento especial
    Responsável). Se o CE já tem Ficha de repressão ABERTA (fase < 3), o contêiner entra nela,
    e aí vale a regra do Fichas: só o responsável (ou com a Ficha sem responsável) inclui;
  - RVF de inspeção não invasiva do contêiner: descrição da carga declarada, memória de cálculo
    do risco na `descricao_interna` (interna) e até MAX_IMAGENS imagens de escaneamento,
    copiadas para o GridFS do Fichas (`MONGODB_RISCO`), cada uma num arquivo PRÓPRIO desta RVF
    (o Fichas apaga o arquivo ao excluir a imagem; um arquivo compartilhado com outra RVF
    sumiria das duas). 5 ou mais imagens fariam o Fichas tratar a RVF como verificação física
    informada (`rvfmanager.gera_evento_rvf`);
  - eventos: Inspeção não invasiva (especial 7) e, se o analista marcou, "Bloqueio de CE
    incluído" e "Verificação Física Agendada" (padrão da EQRIMP na medição de 17/10/2026; não
    são eventos especiais: achados pelo nome, exato).
Repetição (clique duplo): o contêiner que já tem RVF na Ficha aberta não gera nada (devolve a
existente). Falha: desfaz o banco e apaga do GridFS as imagens que esta chamada gravou.

Perfil: como `ovrmanager.cadastra_ovr`, basta o usuário habilitado no Fichas (o código atual não
barra o perfil Consulta na criação).
"""
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from gridfs import GridFS

from bhadrasana.models import (EBloqueado, ENaoAutorizado, ESomenteUsuarioResponsavel, Usuario,
                               get_usuario_validando)
from bhadrasana.models.ovr import EventoEspecial, Flag, OVR, Recinto, TipoEventoOVR
from bhadrasana.models.ovrmanager import gera_eventoovr, valida_mesmo_responsavel_ovr_user_name
from bhadrasana.models.rvf import ImagemRVF, RVF

TIPO_REPRESSAO_IMPORTACAO = 1
FASE_ENCERRADA = 3          # fase >= 3: concluída/arquivada
FLAG_NAVII = 'NAVI-I'
SELO = '[NAVI-I]'
# Observações da Ficha: o campo tem 1.000; 71% das Fichas usam mais de 500 em relatório
TAMANHO_RESUMO = 500
TAMANHO_TEXTO_RVF = 5000    # descricao e descricao_interna da RVF
MAX_IMAGENS = 4
EVENTO_BLOQUEIO = 'bloqueio de ce incluido'
EVENTO_AGENDADA = 'verificacao fisica agendada'


class EFichaNavii(Exception):
    """Erro de negócio com mensagem para o analista (a tela mostra)."""


# Erros com mensagem para o analista (o NAVI-I responde 400 com o texto; os demais são falha)
ERROS_DE_NEGOCIO = (EFichaNavii, ENaoAutorizado, ESomenteUsuarioResponsavel, EBloqueado, KeyError)


@dataclass
class DadosFicha:
    """O que o NAVI-I sabe do card (montado no virasana)."""

    numeroCEmercante: str
    conteiner: str
    resumo_risco: str = ''          # observações da Ficha (o selo [NAVI-I] entra se faltar)
    descricao_carga: str = ''       # RVF.descricao
    memoria_risco: str = ''         # RVF.descricao_interna
    imagens: List[Tuple[bytes, str]] = field(default_factory=list)   # (conteúdo, nome)
    recinto_siscomex: Optional[str] = None
    cnpj_consignatario: Optional[str] = None
    bloqueio_incluido: bool = False
    verificacao_agendada: bool = False


@dataclass
class ResultadoFicha:
    """O que a abertura fez: 'nova', 'acrescentada' (à Ficha aberta) ou 'ja_existia'."""

    ovr_id: int
    rvf_id: int
    acao: str
    eventos: List[str] = field(default_factory=list)
    imagens: int = 0


# ---------------------------------------------------------------- consultas

def _sem_acento(texto: Optional[str]) -> str:
    sem = ''.join(c for c in unicodedata.normalize('NFD', texto or '')
                  if unicodedata.category(c) != 'Mn')
    return ' '.join(sem.lower().split())


def normaliza_conteiner(numero: Optional[str]) -> str:
    return ''.join(c for c in (numero or '').upper() if c.isalnum())


def tipo_especial(session, especial: EventoEspecial) -> TipoEventoOVR:
    tipo = session.query(TipoEventoOVR).filter(
        TipoEventoOVR.eventoespecial == especial.value).first()
    if tipo is None:
        raise EFichaNavii(f'Tipo de evento especial {especial.name} não cadastrado no Fichas.')
    return tipo


def tipo_por_nome(session, nome_sem_acento: str) -> Optional[TipoEventoOVR]:
    """Tipo de evento comum (sem evento especial) pelo nome sem acento nem maiúsculas: exato."""
    comuns = session.query(TipoEventoOVR).filter(TipoEventoOVR.eventoespecial.is_(None))
    return next((t for t in comuns if _sem_acento(t.nome) == nome_sem_acento), None)


def ficha_aberta_de_repressao(session, ce: str) -> Optional[OVR]:
    """A Ficha de repressão na importação ABERTA (fase < 3) mais recente do CE."""
    return (session.query(OVR)
            .filter(OVR.numeroCEmercante == ce,
                    OVR.tipooperacao == TIPO_REPRESSAO_IMPORTACAO,
                    OVR.fase < FASE_ENCERRADA)
            .order_by(OVR.id.desc()).first())


def rvf_do_conteiner(ovr: OVR, conteiner: str) -> Optional[RVF]:
    alvo = normaliza_conteiner(conteiner)
    return next((r for r in ovr.rvfs if normaliza_conteiner(r.numerolote) == alvo), None)


def _resumo_ficha(session, ovr: OVR) -> dict:
    responsavel = None
    if ovr.responsavel_cpf:
        responsavel = session.query(Usuario).filter(
            Usuario.cpf == ovr.responsavel_cpf).one_or_none()
    return {'id': ovr.id, 'tipooperacao': ovr.tipooperacao, 'tipo': ovr.get_tipooperacao(),
            'fase': ovr.fase, 'fase_descricao': ovr.get_fase(),
            'status': ovr.tipoevento.nome if ovr.tipoevento else None,
            'responsavel': (responsavel.nome or '').strip() if responsavel else None,
            'datahora': ovr.datahora.isoformat() if isinstance(ovr.datahora, datetime) else None}


def _impedimento_responsavel(aberta: OVR, cpf: str, responsavel: Optional[str]) -> Optional[str]:
    if aberta.fase > 0 and aberta.responsavel_cpf and aberta.responsavel_cpf != cpf:
        return (f'O CE já tem a Ficha {aberta.id} aberta, com outro responsável '
                f'({responsavel or "-"}): só ele (ou o supervisor, atribuindo-a a você) '
                'pode incluir este contêiner.')
    return None


def previa(session, cpf: str, ce: str, conteiner: str) -> dict:
    """O que a abertura faria, para o diálogo do NAVI-I.

    'acao' (nova | acrescentar | ja_existe), a Ficha alvo, o impedimento (se houver), as outras
    Fichas do CE (qualquer tipo) e os eventos opcionais disponíveis.
    """
    resultado = {'acao': 'nova', 'ficha': None, 'impedimento': _impedimento_usuario(session, cpf),
                 'outras': [],
                 'opcoes': {'bloqueio': tipo_por_nome(session, EVENTO_BLOQUEIO) is not None,
                            'agendada': tipo_por_nome(session, EVENTO_AGENDADA) is not None}}
    aberta = ficha_aberta_de_repressao(session, ce) if ce else None
    if aberta is not None:
        resultado['ficha'] = _resumo_ficha(session, aberta)
        ja_existe = rvf_do_conteiner(aberta, conteiner) is not None
        resultado['acao'] = 'ja_existe' if ja_existe else 'acrescentar'
        if not ja_existe and not resultado['impedimento']:
            resultado['impedimento'] = _impedimento_responsavel(
                aberta, cpf, resultado['ficha']['responsavel'])
    if ce:
        resultado['outras'] = _outras_do_ce(session, ce, aberta)
    return resultado


def _impedimento_usuario(session, cpf: str) -> Optional[str]:
    try:
        get_usuario_validando(session, cpf)
    except (KeyError, ENaoAutorizado):
        return 'Seu usuário não está habilitado no Fichas: peça o cadastro ao supervisor.'
    return None


def _outras_do_ce(session, ce: str, aberta: Optional[OVR]) -> List[dict]:
    """As outras Fichas do CE (qualquer tipo e fase), as 10 mais recentes."""
    do_ce = session.query(OVR).filter(OVR.numeroCEmercante == ce).order_by(OVR.id.desc())
    return [_resumo_ficha(session, o) for o in do_ce.limit(10)
            if aberta is None or o.id != aberta.id]


# ---------------------------------------------------------------- abertura

def _novo(classe, **campos):
    """Instância com os campos atribuídos um a um.

    O `__init__` de `BaseRastreavel` (OVR, RVF, ImagemRVF, EventoOVR) DESCARTA os argumentos
    nomeados (menos `user_name`): `RVF(ovr_id=...)` sairia vazia.
    """
    objeto = classe()
    for nome, valor in campos.items():
        setattr(objeto, nome, valor)
    return objeto


def _texto(texto: Optional[str], limite: int) -> str:
    texto = (texto or '').strip()
    return texto if len(texto) <= limite else texto[:limite - 1] + '…'


def _resumo_com_selo(resumo: str) -> str:
    resumo = ' '.join((resumo or '').split())
    if not resumo.startswith(SELO):
        resumo = f'{SELO} {resumo}'.strip()
    return _texto(resumo, TAMANHO_RESUMO)


def _flag_navii(session) -> Flag:
    flag = session.query(Flag).filter(Flag.nome == FLAG_NAVII).first()
    if flag is None:
        flag = Flag(nome=FLAG_NAVII)
        session.add(flag)
    return flag


def _nova_ficha(session, usuario: Usuario, dados: DadosFicha, agora: datetime) -> OVR:
    cnpj = ''.join(c for c in (dados.cnpj_consignatario or '') if c.isdigit())
    ovr = _novo(OVR, tipooperacao=TIPO_REPRESSAO_IMPORTACAO,
                numeroCEmercante=dados.numeroCEmercante,
                observacoes=_resumo_com_selo(dados.resumo_risco), datahora=agora,
                setor_id=usuario.setor_id, user_name=usuario.cpf, responsavel_cpf=usuario.cpf,
                cnpj_fiscalizado=cnpj or None)
    if dados.recinto_siscomex:
        recinto = session.query(Recinto).filter(
            Recinto.cod_siscomex == dados.recinto_siscomex).first()
        ovr.recinto_id = recinto.id if recinto else None
    ovr.flags.append(_flag_navii(session))
    session.add(ovr)
    session.flush()
    return ovr


def _evento(session, ovr: OVR, tipo: TipoEventoOVR, motivo: str, cpf: str,
            quando: datetime) -> str:
    """Evento pelo `gera_eventoovr` do Fichas, sem commit (fase e status seguem a regra de lá)."""
    gera_eventoovr(session, {'ovr_id': ovr.id, 'tipoevento_id': tipo.id, 'motivo': motivo,
                             'create_date': quando},
                   commit=False, user_name=cpf)
    return tipo.nome


def _grava_imagens(fs: GridFS, session, rvf: RVF, imagens: List[Tuple[bytes, str]],
                   gravadas: list) -> int:
    for ordem, (conteudo, nome) in enumerate(imagens[:MAX_IMAGENS], start=1):
        _id = fs.put(conteudo, filename=f'navii_rvf{rvf.id}_{ordem}_{nome}',
                     metadata={'rvf_id': str(rvf.id)})
        gravadas.append(_id)
        session.add(_novo(ImagemRVF, rvf_id=rvf.id, imagem=str(_id), descricao=nome,
                          ordem=ordem, user_name=rvf.user_name))
    return min(len(imagens), MAX_IMAGENS)


def _grava(session, fs: GridFS, usuario: Usuario, ovr: Optional[OVR], dados: DadosFicha,
           agora: datetime, gravadas: list) -> ResultadoFicha:
    cpf = usuario.cpf
    acao = 'acrescentada' if ovr is not None else 'nova'
    eventos = []
    momentos = (agora + timedelta(seconds=i) for i in range(10))   # ordem dos eventos garantida
    if ovr is None:
        ovr = _nova_ficha(session, usuario, dados, agora)
        eventos.append(_evento(session, ovr, tipo_especial(session, EventoEspecial.Responsavel),
                               f'De: Nenhum Para: {cpf}', cpf, next(momentos)))
    rvf = _novo(RVF, ovr_id=ovr.id, numeroCEmercante=dados.numeroCEmercante,
                numerolote=normaliza_conteiner(dados.conteiner),
                descricao=_texto(dados.descricao_carga, TAMANHO_TEXTO_RVF),
                descricao_interna=_texto(dados.memoria_risco, TAMANHO_TEXTO_RVF),
                inspecaonaoinvasiva=True, datahora=agora, user_name=cpf)
    session.add(rvf)
    session.flush()
    imagens = _grava_imagens(fs, session, rvf, dados.imagens, gravadas)
    inspecao = tipo_especial(session, EventoEspecial.InspecaoNaoInvasiva)
    eventos.append(_evento(session, ovr, inspecao, f'RVF {rvf.id}', cpf, next(momentos)))
    opcionais = ((dados.bloqueio_incluido, EVENTO_BLOQUEIO),
                 (dados.verificacao_agendada, EVENTO_AGENDADA))
    for marcado, nome in opcionais:
        tipo = tipo_por_nome(session, nome) if marcado else None
        if tipo is not None:
            eventos.append(_evento(session, ovr, tipo, f'{SELO} registrado na abertura', cpf,
                                   next(momentos)))
    return ResultadoFicha(ovr.id, rvf.id, acao, eventos, imagens)


def abre_ficha_navii(session, mongodb_fichas, cpf: str, dados: DadosFicha,
                     agora: Optional[datetime] = None) -> ResultadoFicha:
    """Abre a Ficha (ou acrescenta o contêiner à Ficha aberta do CE): ver a docstring do módulo."""
    agora = agora or datetime.now()
    usuario = get_usuario_validando(session, cpf)
    if not dados.numeroCEmercante or not normaliza_conteiner(dados.conteiner):
        raise EFichaNavii('Informe o CE e o contêiner.')
    ovr = ficha_aberta_de_repressao(session, dados.numeroCEmercante)
    if ovr is not None:
        existente = rvf_do_conteiner(ovr, dados.conteiner)
        if existente is not None:
            return ResultadoFicha(ovr.id, existente.id, 'ja_existia')
        valida_mesmo_responsavel_ovr_user_name(session, ovr, cpf)
    fs, gravadas = GridFS(mongodb_fichas), []
    try:
        resultado = _grava(session, fs, usuario, ovr, dados, agora, gravadas)
        session.commit()
    except Exception:
        session.rollback()
        for _id in gravadas:
            fs.delete(_id)
        raise
    return resultado
