from datetime import datetime
from enum import Enum
from typing import Tuple, List

from bhadrasana.models import get_usuario
from bhadrasana.models.laudo import Empresa
from bhadrasana.models.ovr import OVR
from bhadrasana.models.ovrmanager import get_visualizacoes
from bhadrasana.models.rvfmanager import lista_rvfovr
from bhadrasana.models.virasana_manager import get_conhecimento


class TipoExibicao(Enum):
    FMA = 1
    Descritivo = 2
    Ocorrencias = 3
    Empresa = 4


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
             'Último Evento'],
        TipoExibicao.Descritivo:
            ['ID',
             'Data',
             'Tipo Operação',
             'CE Mercante',
             'Declaração',
             'Observações',
             'Criador',
             'Último Evento',
             'Usuário'],
        TipoExibicao.Ocorrencias:
            ['ID',
             'Data',
             'CE Mercante',
             'Observações',
             'Infrações RVFs',
             'Marcas RVFs',
             'Último Evento',
             'Usuário'],
        TipoExibicao.Empresa:
            ['ID',
             'Data',
             'CE Mercante',
             'CNPJ - Nome',
             'Infrações RVFs',
             'Marcas RVFs',
             'Último Evento',
             'Usuário'],
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

    def get_linha(self, ovr: OVR) -> Tuple[int, bool, List]:
        evento_user_descricao = ''
        user_descricao = ''
        tipo_evento_nome = ''
        recinto_nome = ''
        visualizado = False
        data_evento = ovr.create_date
        if len(ovr.historico) > 0:
            evento_atual = ovr.historico[len(ovr.historico) - 1]
            if evento_atual.user_name:
                usuario_evento = get_usuario(self.session, evento_atual.user_name)
                if usuario_evento:
                    evento_user_descricao = usuario_evento.nome
                else:
                    evento_user_descricao = evento_atual.user_name
            tipo_evento_nome = evento_atual.tipoevento.nome
            data_evento = evento_atual.create_date
        if ovr.user_name:
            usuario = get_usuario(self.session, ovr.user_name)
            if usuario:
                user_descricao = usuario.nome
            else:
                user_descricao = ovr.user_name
        if ovr.recinto:
            recinto_nome = ovr.recinto.nome
        visualizacoes = get_visualizacoes(self.session, ovr, self.user_name)
        if len(visualizacoes) > 0:
            max_visualizacao_date = datetime.min
            for visualizacao in visualizacoes:
                max_visualizacao_date = max(visualizacao.create_date,
                                            max_visualizacao_date)
            if max_visualizacao_date > data_evento:
                visualizado = True

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
                tipo_evento_nome]
        if self.tipo == TipoExibicao.Descritivo:
            return ovr.id, visualizado, [
                ovr.datahora,
                ovr.get_tipooperacao(),
                ovr.numeroCEmercante,
                ovr.numerodeclaracao,
                ovr.observacoes,
                user_descricao,
                tipo_evento_nome,
                evento_user_descricao]
        if (self.tipo == TipoExibicao.Ocorrencias or
                self.tipo == TipoExibicao.Empresa):
            infracoes = set()
            marcas = set()
            rvfs = lista_rvfovr(self.session, ovr.id)
            for rvf in rvfs:
                for infracao in rvf.infracoesencontradas:
                    infracoes.add(infracao.nome)
                for marca in rvf.marcasencontradas:
                    marcas.add(marca.nome)
            campo_comum = ''
            if self.tipo == TipoExibicao.Ocorrencias:
                campo_comum = ovr.observacoes
            else:
                conhecimento = get_conhecimento(self.session, ovr.numeroCEmercante)
                if conhecimento:
                    cnpj = conhecimento.consignatario
                    if cnpj:
                        empresa = self.session.query(Empresa).filter(
                            Empresa.cnpj == cnpj).one_or_none()
                        if empresa:
                            campo_comum = empresa.cnpj + ' - ' + empresa.nome

            return ovr.id, visualizado, [
                ovr.datahora,
                ovr.numeroCEmercante,
                campo_comum,
                ', '.join(infracoes),
                ', '.join(marcas),
                tipo_evento_nome,
                evento_user_descricao]

    def get_titulos(self):
        return ExibicaoOVR.titulos[self.tipo]
