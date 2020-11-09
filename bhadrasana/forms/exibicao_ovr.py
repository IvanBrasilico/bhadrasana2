from datetime import datetime
from enum import Enum
from typing import Tuple, List

from bhadrasana.models import get_usuario, usuario_tem_perfil_nome
from bhadrasana.models.laudo import get_empresa
from bhadrasana.models.ovr import OVR
from bhadrasana.models.ovrmanager import get_visualizacoes, lista_tgovr
from bhadrasana.models.rvfmanager import lista_rvfovr
from bhadrasana.models.virasana_manager import get_conhecimento


class TipoExibicao(Enum):
    FMA = 1
    Descritivo = 2
    Ocorrencias = 3
    Empresa = 4
    Resultado = 5
    Resumo = 6


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
             'Alertas',
             'Último Evento',
             'Evento Anterior',
             'Auditor Responsável'],
        TipoExibicao.Descritivo:
            ['ID',
             'Data Ficha',
             'Tipo Operação',
             'CE Mercante',
             'Declaração',
             'Fiscalizado',
             'Observações',
             'Criador',
             'Último Evento',
             'Usuário'],
        TipoExibicao.Ocorrencias:
            ['ID',
             'Data Ficha',
             'CE Mercante',
             'Observações',
             'Infrações RVFs',
             'Marcas RVFs',
             'Último Evento',
             'Evento Anterior'],
        TipoExibicao.Empresa:
            ['ID',
             'Data Ficha',
             'CE Mercante',
             'CNPJ/Nome Fiscalizado',
             'Infrações RVFs',
             'Marcas RVFs',
             'Último Evento',
             'Evento Anterior'],
        TipoExibicao.Resultado:
            ['ID',
             'Data Ficha',
             'CE Mercante',
             'CNPJ/Nome Fiscalizado',
             'Infrações RVFs',
             'Marcas RVFs',
             'Peso apreensões',
             'Valor TG',
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
        if len(ovr.historico) >= ind:
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
        return evento_user_descricao, tipo_evento_nome, data_evento, motivo

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
            empresa = get_empresa(self.session, ovr.cnpj_fiscalizado)
            if empresa:
                fiscalizado = fiscalizado + ' - ' + empresa.nome
        return fiscalizado

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
            conteineres.add(rvf.numerolote)
        return conteineres

    def get_peso_apreensoes(self, ovr):
        peso = 0.
        rvfs = lista_rvfovr(self.session, ovr.id)
        for rvf in rvfs:
            for apreensao in rvf.apreensoes:
                try:
                    peso += float(apreensao.peso)
                except TypeError:
                    pass
        return peso

    def get_valor_tgs(self, ovr):
        valor = 0.
        tgs = lista_tgovr(self.session, ovr.id)
        for tg in tgs:
            try:
                valor += float(tg.valor)
            except TypeError:
                pass
        return valor

    def get_linha(self, ovr: OVR) -> Tuple[int, bool, List]:
        recinto_nome = self.get_recinto_nome(ovr)
        evento_user, tipo_evento_nome, data_evento, motivo = self.evento_campos(ovr)
        campos_ultimo_evento = [tipo_evento_nome, evento_user,
                                datetime.strftime(data_evento, '%d/%m/%Y %H:%M'),
                                motivo]
        html_ultimo_evento = '<br>'.join(campos_ultimo_evento)
        evento_user2, tipo_evento_nome2, data_evento2, motivo2 = self.evento_campos(ovr, 2)
        campos_penultimo_evento = [tipo_evento_nome2, evento_user2,
                                   datetime.strftime(data_evento2, '%d/%m/%Y %H:%M'),
                                   motivo2]
        html_penultimo_evento = '<br>'.join(campos_penultimo_evento)
        user_descricao = self.usuario_name(ovr.user_name)
        auditor_descricao = self.usuario_name(ovr.cpfauditorresponsavel)
        visualizado = self.get_visualizado_pelo_usuario(ovr, data_evento)
        fiscalizado = self.get_fiscalizado(ovr)
        if self.tipo == TipoExibicao.FMA:
            alertas = [flag.nome for flag in ovr.flags]
            return ovr.id, visualizado, [
                ovr.datahora,
                ovr.get_tipooperacao(),
                recinto_nome,
                ovr.get_ano(),
                ovr.numero,
                ovr.numeroCEmercante,
                ', '.join(alertas),
                html_ultimo_evento,
                html_penultimo_evento,
                auditor_descricao]
        if self.tipo == TipoExibicao.Descritivo:
            return ovr.id, visualizado, [
                ovr.datahora,
                ovr.get_tipooperacao(),
                ovr.numeroCEmercante,
                ovr.numerodeclaracao,
                fiscalizado,
                ovr.observacoes,
                user_descricao,
                html_ultimo_evento,
                html_penultimo_evento]
        if (self.tipo == TipoExibicao.Ocorrencias or
                self.tipo == TipoExibicao.Empresa):
            infracoes, marcas = self.get_infracoes_e_marcas(ovr)
            if self.tipo == TipoExibicao.Ocorrencias:
                campo_comum = ovr.observacoes
            else:
                campo_comum = fiscalizado
            return ovr.id, visualizado, [
                ovr.datahora,
                ovr.numeroCEmercante,
                campo_comum,
                ', '.join(infracoes),
                ', '.join(marcas),
                html_ultimo_evento,
                html_penultimo_evento]
        if self.tipo == TipoExibicao.Resultado:
            infracoes, marcas = self.get_infracoes_e_marcas(ovr)
            peso_apreensoes = self.get_peso_apreensoes(ovr)
            valor_tgs = self.get_valor_tgs(ovr)
            return ovr.id, visualizado, [
                ovr.datahora,
                ovr.numeroCEmercante,
                fiscalizado,
                ', '.join(infracoes),
                ', '.join(marcas),
                '{:0.2f}'.format(peso_apreensoes),
                '{:0.2f}'.format(valor_tgs),
                auditor_descricao]
        if self.tipo == TipoExibicao.Resumo:
            resumo = self.get_OVR_resumo_html(ovr)
            return ovr.id, visualizado, [
                ovr.datahora,
                auditor_descricao,
                html_ultimo_evento,
                html_penultimo_evento,
                fiscalizado,
                resumo]

    def get_mercante_resumo(self, ovr) -> list:
        resumo = []
        conhecimento = get_conhecimento(self.session,
                                        ovr.numeroCEmercante)
        if conhecimento:
            resumo.append(f'<b>BL</b>: {conhecimento.numConhecimento}')
            conteineres = self.get_conteineres(ovr)
            if conteineres:
                resumo.append(f'<b>Contêineres</b>: {conteineres}')
            resumo.append(f'<b>Porto de Origem</b>: {conhecimento.portoOrigemCarga}')
            resumo.append(f'<b>Porto de Destino Final</b>: {conhecimento.portoDestFinal}')
            resumo.append(f'<b>Mercadoria</b>: {conhecimento.descricao}')
            resumo.append(f'<b>M3</b>: {conhecimento.cubagem}')
        return resumo

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

    def get_OVR_resumo(self, ovr, mercante=True,
                       fiscalizado=False, eventos=False,
                       responsaveis=False, trabalho=False,
                       responsabilidade=False) -> list:
        datahora = ovr.datahora.strftime('%d/%m/%Y') if ovr.datahora else ''
        resumo = [f'<h4><a href="ovr?id={ovr.id}" style="color: orange" target="_blank">' +
                  f'{ovr.id} - {datahora}</a></h4>{ovr.get_tipooperacao()}']
        if ovr.observacoes:
            resumo.append(ovr.observacoes)
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
        if responsaveis:
            resumo.extend(self.get_responsaveis_resumo(ovr))
        if responsabilidade:
            resumo.extend(self.get_responsabilidade_resumo(ovr))
        if trabalho:
            resumo.extend(self.get_trabalho(ovr))
        if mercante:
            resumo.extend(self.get_mercante_resumo(ovr))
        if eventos:
            resumo.extend(self.get_eventos_resumo(ovr))
        return resumo

    def get_titulos(self):
        return ExibicaoOVR.titulos[self.tipo]

    def get_eventos_resumo(self, ovr) -> list:
        resumo = []
        for evento in ovr.historico[:-3]:
            resumo.append('{} - {} - {} - {}'.format(
                evento.tipoevento.nome, evento.user_name,
                datetime.strftime(evento.create_date, '%d/%m/%Y %H:%M'), evento.motivo))
        return resumo

    def get_responsaveis_resumo(self, ovr) -> list:
        resumo = []
        if ovr.user_name:
            user_descricao = self.usuario_name(ovr.user_name)
            resumo.append(f'<b>Criador:</b>{ovr.user_name} - {user_descricao}')
        if ovr.responsavel:
            resumo.append(f'<b>Atribuído a:</b>{ovr.responsavel}')
        if ovr.cpfauditorresponsavel:
            auditor_descricao = self.usuario_name(ovr.cpfauditorresponsavel)
            resumo.append(f'<b>Auditor:</b>{ovr.cpfauditorresponsavel} - {auditor_descricao}')
        return resumo

    def get_responsabilidade_resumo(self, ovr) -> list:
        linha = []
        if self.user_name == ovr.user_name:
            linha.append('<span class="badge badge-pill">Criador</span>')
        if self.user_name == ovr.responsavel:
            linha.append('<span class="badge badge-pill">Responsável atual</span>')
        if self.user_name == ovr.cpfauditorresponsavel:
            linha.append('<span class="badge badge-pill">Auditor responsável</span>')
        if usuario_tem_perfil_nome(self.session, self.user_name, 'Supervisor'):
            linha.append('<span class="badge badge-pill">Supervisor</span>')
        return [' '.join(linha)]

    def get_trabalho(self, ovr) -> list:
        tipos_evento = set([evento.tipoevento_id for evento in ovr.historico])
        return ['Progresso: ' + '&FilledSmallSquare;' * len(tipos_evento)]
