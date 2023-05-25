import calendar
from collections import OrderedDict

from bhadrasana.models import Usuario
from bhadrasana.models.rvfmanager import lista_rvfovr


def preenche_linha_ovr(operacao, year, month):
    lastday = calendar.monthrange(year, month)[1]
    ano = str(year)
    mes = str(month).zfill(2)
    inicio = f'01/{mes}/{ano}'
    termino = f'{lastday}/{mes}/{ano}'
    campos_ovr = OrderedDict()
    NOMES_TIPOOPERACAO = {
        1: f'IMPORTAÇÃO - OPERAÇÃO LUNETA {ano}{mes}',
        # Observação: ideal seria dividir mais as OVRs, pois além de Operação Luneta, tivemos Outlet, Ramenta, temos a seleção de
        # bagagem, etc. Mas aí precisaria ser "Hard-coded" o agrupamento por OVRs
        2: f'EXPORTAÇÃO - OPERAÇÃO PORTO BLINDADO {ano}{mes}',
        # Observação: hoje não temos, mas se fizermos OUTROS TIPOS DE OPERAÇÕES em exportação que não a habitual busca de cocaína,
        # o ideal seria separar em outras OVRs
        3: f'IMPORTAÇÃO - ANÁLISE DE RISCO E DE IMAGENS - OPERAÇÃO LUNETA {ano}{mes}',
        # Observação: ideal seria dividir mais as OVRs, pois além de Operação Luneta, tivemos Outlet, Ramenta, temos a seleção de
        # bagagem, etc. Mas aí precisaria ser "Hard-coded" o agrupamento por OVRs
        4: f'EXPORTAÇÃO - ANÁLISE DE RISCO E DE IMAGENS - OPERAÇÃO PORTO BLINDADO {ano}{mes}',
        # Observação: existe também o código "Pós-incidente" e não temos distinção no Fichas, vamos criar um Flag.
        # no caso deste flag, substituir estes campos por 'Tipo': 'Pós-Incidente - Portos', 'Código': '30.02.10'
        7: f'VIGILÂNCIA - OPERAÇÃO REDOMA {ano}{mes}',
    }
    campos_ovr['Nome'] = NOMES_TIPOOPERACAO[operacao.tipooperacao]
    if operacao.tipooperacao in (1, 2):
        campos_ovr['Modalidade'] = 'Vigilância e Repressão'
        campos_ovr['Tipo'] = 'Portos'
        campos_ovr['Código'] = '20.00.10'
    elif operacao.tipooperacao in (3, 4):
        campos_ovr['Modalidade'] = 'Pesquisa e Seleção'
        campos_ovr['Tipo'] = 'Pré-Incidente - Portos'
        campos_ovr['Código'] = '30.01.10'
    elif operacao.tipooperacao == 7:
        campos_ovr['Modalidade'] = 'Vigilância e Repressão'
        # Observação: Secta e-OVR não possui a tipificação de vigilância/rondas, auditorias e conformidade
        # Utilizando este tipo e código para distinção
        campos_ovr['Tipo'] = 'Ponto de fronteira'
        campos_ovr['Código'] = '20.00.09'
    else:
        raise Exception(f'tipooperacao {operacao.tipooperacao} não previsto!!')
    campos_ovr['Abrangência'] = 'Local'
    campos_ovr['Início'] = inicio
    campos_ovr['Término'] = termino
    campos_ovr['Local da Execução'] = 'Porto de Santos'
    campos_ovr['Coordenador'] = 'Ivan da Silva Brasílico'
    campos_ovr['Coordenador_CPF'] = '25052288840'
    campos_ovr['Motivação'] = 'Demanda Interna'
    # Por último, analisa Flags para mudar Descrição da Operação
    if len(operacao.flags) > 0:
        flags = [flag for flag in operacao.flags]
        for flag in flags:
            if 'Operação' in flag.nome:
                campos_ovr['Nome'] = flag.nome + f' {ano}{mes}'
                break
            if flag.nome == 'Pós incidente':
                campos_ovr['Nome'] = 'Pós-Incidente - ' + campos_ovr['Nome']
                campos_ovr['Tipo'] = 'Pós-Incidente - Portos'
                campos_ovr['Código'] = '30.02.10'
    return campos_ovr


def get_peso_apreensoes(session, rvfs):
    peso = 0.
    for rvf in rvfs:
        for apreensao in rvf.apreensoes:
            try:
                peso += float(apreensao.peso)
            except TypeError:
                pass
    return peso


def get_valor_tgs(ovr):
    valor = 0.
    for tg in ovr.tgs:
        try:
            valor += float(tg.valor)
        except TypeError:
            pass
    return valor


def preenche_linha_operacao(db_session, operacao, modalidade):
    linha = OrderedDict()
    linha['Órgão'] = 'RFB'
    linha['Equipe'] = operacao.setor.nome
    linha['Modalidade Operação'] = modalidade
    linha['Tipo'] = 'Portos'
    linha['Local da Operação'] = operacao.recinto.nome
    linha['Documentos de origem'] = f'Ficha {operacao.id}'
    linha['Ocorrências durante a operação'] = operacao.observacoes
    linha['Supervisor da RFB'] = str(operacao.cpfauditorresponsavel)
    linha['Responsável'] = str(operacao.responsavel_cpf)
    rvfs = lista_rvfovr(db_session, operacao.id)
    valortgs = get_valor_tgs(operacao)
    pesoapreensoes = get_peso_apreensoes(db_session, rvfs)
    nhoras = len(rvfs) * 8
    if valortgs > 0:
        nhoras = nhoras * 5
    if pesoapreensoes > 0:
        nhoras = nhoras * 2
    servidores_set = set()
    for evento in operacao.historico:
        servidores_set.add(evento.user_name)
    servidores = []
    for lcpf in servidores_set:
        servidor = db_session.query(Usuario).filter(Usuario.cpf == lcpf).one()
        servidores.append({'cpf': servidor.cpf, 'nome': servidor.nome, 'horas': nhoras})
    linha['Servidores'] = servidores
    linha['Perdimento'] = valortgs
    linha['Apreensao'] = pesoapreensoes
    return linha
