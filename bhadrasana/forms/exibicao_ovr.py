from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Tuple, List

from bhadrasana.models import get_usuario
from bhadrasana.models.laudo import get_empresa, get_pessoa
from bhadrasana.models.ovr import OVR
from bhadrasana.models.ovrmanager import get_visualizacoes, lista_tgovr
from bhadrasana.models.rvfmanager import lista_rvfovr
from bhadrasana.models.virasana_manager import get_conhecimento, get_ncms_conhecimento
from virasana.integracao.due.due_manager import get_itens_due, get_due_view


class TipoExibicao(Enum):
    FMA = 1
    Descritivo = 2
    Ocorrencias = 3
    Empresa = 4
    Resultado = 5
    Resumo = 6
    FMA_2 = 7


def agrupa_ovrs(ovrs, listaovrs, campo):
    listaagrupada = defaultdict(list)
    if campo and campo != 'None':
        for ovr, exibicao_linha in zip(ovrs, listaovrs):
            if campo == 'fase':
                grupo = ovr.get_fase()
            elif campo == 'recinto_id':
                try:
                    grupo = ovr.recinto.nome
                except:
                    grupo = None
            else:
                grupo = getattr(ovr, campo)
            listaagrupada[grupo].append(exibicao_linha)
    else:
        listaagrupada['Sem grupos'] = listaovrs
    return listaagrupada


class ExibicaoOVR:
    tipos = TipoExibicao

    titulos = {
        TipoExibicao.FMA:
            ['ID',
             'Data',
             'Tipo Operação',
             'Recinto',
             'Ano',
             'Número doc.',
             'CE Mercante',
             'CNPJ Fiscalizado',
             'Nome Fiscalizado',
             'Alertas',
             'Último Evento',
             'Evento Anterior',
             'Responsável atual',
             'Auditor Responsável'],
        TipoExibicao.FMA_2:
            ['ID',
             'Data',
             'Tipo Operação',
             'Recinto',
             'Ano',
             'Número doc.',
             'CE Mercante',
             'Alertas',
             'Observações',
             'Mercadoria',
             'Lista de NCMs'],
        TipoExibicao.Descritivo:
            ['ID',
             'Data Ficha',
             'Tipo Operação',
             'CE Mercante',
             'Declaração',
             'Fiscalizado',
             'Observações',
             'Responsável atual',
             'Último Evento',
             'Usuário'],
        TipoExibicao.Ocorrencias:
            ['ID',
             'Data Ficha',
             'CE Mercante',
             'Observações',
             'Infrações RVFs',
             'Marcas RVFs',
             'Responsável atual',
             'Último Evento',
             'Evento Anterior'],
        TipoExibicao.Empresa:
            ['ID',
             'Data Ficha',
             'CE Mercante',
             'CNPJ/Nome Fiscalizado',
             'Infrações RVFs',
             'Marcas RVFs',
             'Responsável atual',
             'Último Evento',
             'Evento Anterior'],
        TipoExibicao.Resultado:
            ['ID',
             'Data Ficha',
             'CE Mercante',
             'CNPJ/Nome Fiscalizado',
             'Descrição',
             'Infrações RVFs',
             'Marcas RVFs',
             'Peso apreensões',
             'Valor TG',
             'Resultados informados',
             'Processos',
             'Auditor Responsável'],
        TipoExibicao.Resumo:
            ['ID',
             'Data Ficha',
             'Auditor Responsável',
             'Último Evento',
             'Evento Anterior',
             'CNPJ/Nome Fiscalizado',
             'Resumo para compartilhamento',
             ],
    }

    def __init__(self, session, tipo, user_name: str):
        self.session = session
        self.user_name = user_name
        if isinstance(tipo, str):
            self.tipo = TipoExibicao[tipo]
        elif isinstance(tipo, int):
            self.tipo = TipoExibicao(tipo)
        elif isinstance(tipo, TipoExibicao):
            self.tipo = tipo
        else:
            raise TypeError(
                'Deve ser informado parâmetro do tipo TipoExibicao, str ou int')

    def evento_campos(self, ovr, ind=1):
        """Retorna campos do evento -ind da ovr

        :param ovr: OVR
        :param ind: índice inverso (1 último, 2 penúltimo, etc)
        :return: evento_user_descricao: Nome do Usuário do Evento,
                tipo_evento_nome: Nome do Tipo de Evento,
                 data_evento: Data de ocorrência do Evento
        """
        tipo_evento_nome = ''
        data_evento = ovr.create_date
        evento_user_descricao = ''
        motivo = ''
        ind_aux = ind
        if len(ovr.historico) >= ind:
            while ovr.historico[len(ovr.historico) - ind].meramente_informativo or \
                    'atribuição' in ovr.historico[len(ovr.historico) - ind].tipoevento.nome.lower():
                ind += 1
                if ind >= len(ovr.historico):
                    break
            if ind >= len(ovr.historico):
                ind = ind_aux
            evento_atual = ovr.historico[len(ovr.historico) - ind]
            if evento_atual.user_name:
                usuario_evento = get_usuario(self.session, evento_atual.user_name)
                if usuario_evento:
                    evento_user_descricao = usuario_evento.nome
                else:
                    evento_user_descricao = evento_atual.user_name
            tipo_evento_nome = evento_atual.tipoevento.nome
            data_evento = evento_atual.create_date
            motivo = evento_atual.motivo
        return evento_user_descricao, tipo_evento_nome, data_evento, motivo, ind

    def usuario_name(self, user_name):
        user_descricao = ''
        if user_name:
            usuario = get_usuario(self.session, user_name)
            if usuario:
                user_descricao = usuario.nome
            else:
                user_descricao = user_name
        return user_descricao

    def get_visualizado_pelo_usuario(self, ovr, data_evento):
        visualizado = False
        visualizacoes = get_visualizacoes(self.session, ovr, self.user_name)
        if len(visualizacoes) > 0:
            max_visualizacao_date = datetime.min
            for visualizacao in visualizacoes:
                max_visualizacao_date = max(visualizacao.create_date,
                                            max_visualizacao_date)
            if max_visualizacao_date > data_evento:
                visualizado = True
        return visualizado

    def get_fiscalizado(self, ovr):
        fiscalizado = ''
        if ovr.cnpj_fiscalizado:
            fiscalizado = ovr.cnpj_fiscalizado
            try:
                empresa = get_empresa(self.session, ovr.cnpj_fiscalizado)
                if empresa:
                    fiscalizado = fiscalizado + ' - ' + empresa.nome
            except ValueError:
                pass
        return fiscalizado

    def get_fiscalizado_cnpj_nome(self, ovr):
        fiscalizado_cnpj = ''
        fiscalizado_nome = ''
        if ovr.cnpj_fiscalizado:
            fiscalizado_cnpj = ovr.cnpj_fiscalizado
            try:
                fiscalizado = None
                if ovr.cnpj_fiscalizado and len(ovr.cnpj_fiscalizado) == 11:
                    fiscalizado = get_pessoa(self.session, ovr.cnpj_fiscalizado)
                if not fiscalizado:
                    fiscalizado = get_empresa(self.session, ovr.cnpj_fiscalizado)
                if fiscalizado:
                    fiscalizado_nome = fiscalizado.nome
            except ValueError:
                pass
        return fiscalizado_cnpj, fiscalizado_nome

    def get_recinto_nome(self, ovr):
        recinto_nome = ''
        if ovr.recinto:
            recinto_nome = ovr.recinto.nome
        return recinto_nome

    def get_infracoes_e_marcas(self, ovr):
        infracoes = set()
        marcas = set()
        rvfs = lista_rvfovr(self.session, ovr.id)
        for rvf in rvfs:
            for infracao in rvf.infracoesencontradas:
                infracoes.add(infracao.nome)
            for marca in rvf.marcasencontradas:
                marcas.add(marca.nome)
        return infracoes, marcas

    def get_conteineres(self, ovr):
        conteineres = set()
        rvfs = lista_rvfovr(self.session, ovr.id)
        for rvf in rvfs:
            if rvf.numerolote:
                conteineres.add(rvf.numerolote)
        return conteineres

    def get_peso_apreensoes(self, ovr) -> float:
        peso = 0.
        rvfs = lista_rvfovr(self.session, ovr.id)
        for rvf in rvfs:
            for apreensao in rvf.apreensoes:
                try:
                    peso += float(apreensao.peso)
                except TypeError:
                    pass
        return peso

    def get_datas_verificacoes(self, ovr) -> List[str]:
        lista_datas = []
        rvfs = lista_rvfovr(self.session, ovr.id)
        for rvf in rvfs:
            if rvf.datahora:
                lista_datas.append(rvf.datahora.strftime('%d/%m/%Y'))
        return lista_datas

    def get_valor_tgs(self, ovr):
        valor = 0.
        tgs = lista_tgovr(self.session, ovr.id)
        for tg in tgs:
            try:
                valor += float(tg.valor)
            except TypeError:
                pass
        return valor

    def get_linha(self, ovr: OVR) -> Tuple[int, bool, List, bool]:
        recinto_nome = self.get_recinto_nome(ovr)
        evento_user, tipo_evento_nome, data_evento, motivo, ind = self.evento_campos(ovr)
        campos_ultimo_evento = [f'<b>{tipo_evento_nome}</b>', evento_user,
                                datetime.strftime(data_evento, '%d/%m/%Y %H:%M'),
                                motivo]
        html_ultimo_evento = '<br>'.join(campos_ultimo_evento)
        evento_user2, tipo_evento_nome2, data_evento2, motivo2, ind2 = \
            self.evento_campos(ovr, ind + 1)
        campos_penultimo_evento = [f'<b>{tipo_evento_nome2}</b>', evento_user2,
                                   datetime.strftime(data_evento2, '%d/%m/%Y %H:%M'),
                                   motivo2]
        html_penultimo_evento = '<br>'.join(campos_penultimo_evento)
        # user_descricao = self.usuario_name(ovr.user_name)
        auditor_descricao = self.usuario_name(ovr.cpfauditorresponsavel)
        visualizado = self.get_visualizado_pelo_usuario(ovr, data_evento)
        fiscalizado = self.get_fiscalizado(ovr)
        responsavel_descricao = 'Nenhum'
        if ovr.responsavel:
            responsavel_descricao = ovr.responsavel.nome
        alertas = [flag.nome for flag in ovr.flags]
        e_perecivel = 'perecível' in ''.join(alertas).lower()
        if self.tipo == TipoExibicao.FMA:
            fiscalizado_cnpj, fiscalizado_nome = self.get_fiscalizado_cnpj_nome(ovr)
            return ovr.id, visualizado, [
                ovr.datahora,
                ovr.get_tipooperacao(),
                recinto_nome,
                ovr.get_ano(),
                ovr.numero,
                ovr.numeroCEmercante,
                fiscalizado_cnpj,
                fiscalizado_nome,
                ', '.join(alertas),
                html_ultimo_evento,
                html_penultimo_evento,
                responsavel_descricao,
                auditor_descricao], e_perecivel
        if self.tipo == TipoExibicao.FMA_2:
            mercadoria, lista_de_ncms = self.get_mercadoria_mercante(ovr)
            return ovr.id, visualizado, [
                ovr.datahora,
                ovr.get_tipooperacao(),
                recinto_nome,
                ovr.get_ano(),
                ovr.numero,
                ovr.numeroCEmercante,
                ', '.join(alertas),
                str(ovr.observacoes or ''),
                mercadoria,
                lista_de_ncms], e_perecivel
        if self.tipo == TipoExibicao.Descritivo:
            return ovr.id, visualizado, [
                ovr.datahora,
                ovr.get_tipooperacao(),
                ovr.numeroCEmercante,
                ovr.numerodeclaracao,
                fiscalizado,
                str(ovr.observacoes or ''),
                responsavel_descricao,
                html_ultimo_evento,
                html_penultimo_evento], e_perecivel
        if (self.tipo == TipoExibicao.Ocorrencias or
                self.tipo == TipoExibicao.Empresa):
            infracoes, marcas = self.get_infracoes_e_marcas(ovr)
            if self.tipo == TipoExibicao.Ocorrencias:
                campo_comum = str(ovr.observacoes or '')
            else:
                campo_comum = fiscalizado
            return ovr.id, visualizado, [
                ovr.datahora,
                ovr.numeroCEmercante,
                campo_comum,
                ', '.join(infracoes),
                ', '.join(marcas),
                responsavel_descricao,
                html_ultimo_evento,
                html_penultimo_evento], e_perecivel
        if self.tipo == TipoExibicao.Resultado:
            infracoes, marcas = self.get_infracoes_e_marcas(ovr)
            peso_apreensoes = self.get_peso_apreensoes(ovr)
            valor_tgs = self.get_valor_tgs(ovr)
            resultados = []
            for resultado in ovr.resultados:
                resultados.append(f'<b>{resultado.get_tipo_resultado}:</b> {resultado.valor :,.2f}<br>')
            processos = []
            for processo in ovr.processos:
                processos.append(processo.numero)
            return ovr.id, visualizado, [
                ovr.datahora,
                ovr.numeroCEmercante,
                fiscalizado,
                str(ovr.observacoes or ''),
                ', '.join(infracoes),
                ', '.join(marcas),
                '{:0.2f}'.format(peso_apreensoes),
                '{:0.2f}'.format(valor_tgs),
                '\n'.join(resultados),
                ', '.join(processos),
                auditor_descricao], e_perecivel
        if self.tipo == TipoExibicao.Resumo:
            resumo = self.get_OVR_resumo_html(ovr)
            return ovr.id, visualizado, [
                ovr.datahora,
                auditor_descricao,
                html_ultimo_evento,
                html_penultimo_evento,
                fiscalizado,
                resumo], e_perecivel

    def get_mercante_resumo(self, ovr) -> list:
        resumo = []
        conhecimento = get_conhecimento(self.session,
                                        ovr.numeroCEmercante)
        if conhecimento:
            resumo.append(f'<b>BL</b>: {conhecimento.numConhecimento}')
            conteineres = self.get_conteineres(ovr)
            if conteineres:
                lista_conteiner = ', '.join(conteineres)
                resumo.append(f'<b>Contêineres</b>: {lista_conteiner}')
            resumo.append(f'<b>Porto de Origem</b>: {conhecimento.portoOrigemCarga}')
            resumo.append(f'<b>Porto de Destino Final</b>: {conhecimento.portoDestFinal}')
            resumo.append(f'<b>Mercadoria</b>: {conhecimento.descricao}')
            resumo.append(f'<b>M3</b>: {conhecimento.cubagem}')
        return resumo

    def get_due_resumo(self, ovr) -> list:
        resumo = []
        due = get_due_view(self.session,
                           ovr.numerodeclaracao)
        if due:
            resumo.append(f'<b>Declarante</b>: {due.ni_declarante} - {due.nome_declarante}')
            resumo.append(f'<b>Exportador</b>: {due.cnpj_estabelecimento_exportador}')
            resumo.append(f'<b>Recinto Despacho</b>: {due.codigo_recinto_despacho} - {due.nome_recinto_despacho}')
            resumo.append(f'<b>Recinto Embarque</b>: {due.codigo_recinto_embarque} - {due.nome_recinto_embarque}')
            resumo.append(f'<b>País Importador</b>: {due.nome_pais_importador}')
            itens = get_itens_due(self.session, due.numero_due)
            for item in itens:
                resumo.append(f'<b>Mercadoria</b>: {item.due_nr_item} - '
                              f'{item.pais_destino_item} - {item.descricao_item}')
        return resumo

    def get_mercadoria_mercante(self, ovr) -> Tuple[str, str]:
        mercadoria = ''
        lista_ncms = ''
        conhecimento = get_conhecimento(self.session, ovr.numeroCEmercante)
        if conhecimento:
            mercadoria = str(conhecimento.descricao)
            ncms = get_ncms_conhecimento(self.session, ovr.numeroCEmercante)
            lista_ncms = ', '.join([ncm.identificacaoNCM for ncm in ncms])
        return mercadoria, lista_ncms

    def get_OVR_resumo_html(self, ovr, mercante=True,
                            fiscalizado=False, eventos=False,
                            responsaveis=False, trabalho=False,
                            responsabilidade=False) -> str:
        resumo = self.get_OVR_resumo(ovr,
                                     mercante=mercante,
                                     fiscalizado=fiscalizado,
                                     eventos=eventos,
                                     responsaveis=responsaveis,
                                     trabalho=trabalho,
                                     responsabilidade=responsabilidade)

        return '<br>'.join(resumo)

    def get_OVR_resumo(self, ovr, mostra_ovr=True, mercante=True,
                       fiscalizado=False, eventos=False,
                       responsaveis=False, trabalho=False,
                       responsabilidade=False, due=True) -> list:
        datahora = ovr.datahora.strftime('%d/%m/%Y') if ovr.datahora else ''
        resumo = [f'<h4><a href="ovr?id={ovr.id}" style="color: orange" target="_blank">' +
                  f'{ovr.id} - {datahora}</a></h4>{ovr.get_tipooperacao()}']
        datasapreensoes = self.get_datas_verificacoes(ovr)
        resumo.append(f'<b>Aberturas</b>: {", ".join(datasapreensoes)}')
        if mostra_ovr:
            if ovr.setor:
                resumo.append(f'<b>Setor</b>: {ovr.setor.nome}')
            if ovr.numerodeclaracao:
                resumo.append(f'<b>Número Declaração</b>: {ovr.numerodeclaracao}')
            if ovr.observacoes:
                resumo.append(str(ovr.observacoes or ''))
            if len(ovr.flags) > 0:
                resumo.append(f'<b>Alertas</b>: {[str(flag) for flag in ovr.flags]}')
            if fiscalizado:
                fiscalizado = self.get_fiscalizado(ovr)
                if fiscalizado:
                    resumo.append(f'<b>Fiscalizado</b>: {fiscalizado}')
            peso_apreensoes = self.get_peso_apreensoes(ovr)
            if peso_apreensoes:
                resumo.append(f'<b>Peso das Apreensões</b>: {peso_apreensoes}')
            infracoes, marcas = self.get_infracoes_e_marcas(ovr)
            if infracoes:
                resumo.append(f'<b>Infrações</b>: {infracoes}')
            if marcas:
                resumo.append(f'<b>Marcas contrafeitas</b>: {marcas}')
            valor_tgs = self.get_valor_tgs(ovr)
            if valor_tgs:
                resumo.append(f'<b>Valor dos TGs</b>: {valor_tgs}')
            for resultado in ovr.resultados:
                resumo.append(f'<b>{resultado.get_tipo_resultado}:</b> {resultado.valor :,.2f}')
        if responsaveis:
            resumo.extend(self.get_responsaveis_resumo(ovr))
        if responsabilidade:
            resumo.extend(self.get_responsabilidade_resumo(ovr))
        if trabalho:
            resumo.extend(self.get_trabalho(ovr))
        if mercante:
            resumo.extend(self.get_mercante_resumo(ovr))
        if due:
            resumo.extend(self.get_due_resumo(ovr))
        if eventos:
            resumo.extend(self.get_eventos_resumo(ovr))

        return resumo

    def get_titulos(self):
        return ExibicaoOVR.titulos[self.tipo]

    def get_eventos_resumo(self, ovr) -> list:
        resumo = []
        for evento in ovr.historico:
            if 'atribuição' in evento.tipoevento.nome.lower():  # Elimina eventos de atribuição
                continue
            resumo.append('{} - {} - {} - {}'.format(
                evento.tipoevento.nome, evento.user_name,
                datetime.strftime(evento.create_date, '%d/%m/%Y %H:%M'), evento.motivo))
        return resumo

    def get_responsaveis_resumo(self, ovr) -> list:
        resumo = []
        if ovr.user_name:
            user_descricao = self.usuario_name(ovr.user_name)
            resumo.append(f'<b>Cadastrador: </b>{ovr.user_name} - {user_descricao}')
        if ovr.responsavel:
            resumo.append(f'<b>Atribuído atualmente a: </b>{ovr.responsavel}')
        if ovr.cpfauditorresponsavel:
            auditor_descricao = self.usuario_name(ovr.cpfauditorresponsavel)
            resumo.append('<b>Auditor responsável: </b>' +
                          f'{ovr.cpfauditorresponsavel} - {auditor_descricao}')
        return resumo

    def get_responsabilidade_resumo(self, ovr) -> list:
        linha = []
        if self.user_name == ovr.user_name:
            linha.append('<span class="badge badge-pill">Criado por mim</span>')
        if self.user_name == ovr.responsavel_cpf:
            linha.append('<span class="badge badge-pill">Sou Responsável atual</span>')
        if self.user_name == ovr.cpfauditorresponsavel:
            linha.append('<span class="badge badge-pill">Sou Auditor responsável</span>')
        if len(linha) == 0:
            linha.append('<span class="badge badge-pill">Está no meu Setor</span>')
        return [' '.join(linha)]

    def get_trabalho(self, ovr) -> list:
        tipos_evento = set([evento.tipoevento_id for evento in ovr.historico])
        return ['Progresso: ' + '&FilledSmallSquare;' * len(tipos_evento)]
