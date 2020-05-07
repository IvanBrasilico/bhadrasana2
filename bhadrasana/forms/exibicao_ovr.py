from enum import Enum

from bhadrasana.models.ovr import OVR


class TipoExibicao(Enum):
    FMA = 1
    descritivo = 2


class ExibicaoOVR:
    tipos = TipoExibicao

    titulos = {
        TipoExibicao.FMA:
            ['ID',
             'Tipo Operação',
             'Recinto',
             'Ano',
             'Número doc.',
             'CE Mercante',
             'Data',
             'Último Evento'],
        TipoExibicao.descritivo:
            ['ID',
             'Data',
             'Tipo Operação',
             'CE Mercante',
             'Observações',
             'Criador',
             'Último Evento',
             'Usuário'],
    }

    def __init__(self, tipo: TipoExibicao):
        self.tipo = tipo

    def get_linha(self, ovr: OVR):
        if self.tipo == TipoExibicao.FMA:
            return [ovr.id,
                    ovr.get_tipooperacao(),
                    ovr.recinto.nome,
                    ovr.get_ano(),
                    ovr.numero,
                    ovr.numeroCEmercante,
                    ovr.datahora,
                    ovr.tipoevento.nome]
        if self.tipo == TipoExibicao.descritivo:
            evento_user_name = ''
            tipo_evento_nome = ''
            if len(ovr.historico) > 0:
                evento_atual = ovr.historico[len(ovr.historico) - 1]
                evento_user_name = evento_atual.user_name
                tipo_evento_nome = evento_atual.tipoevento.nome
            return [ovr.id,
                    ovr.datahora,
                    ovr.get_tipooperacao(),
                    ovr.numeroCEmercante,
                    ovr.observacoes,
                    ovr.user_name,
                    tipo_evento_nome,
                    evento_user_name]

    def get_titulos(self):
        return ExibicaoOVR.titulos[self.tipo]
