from enum import Enum


class TipoExibicao(Enum):
    FMA = 1
    descritivo = 2


class ExibicaoOVR:
    tipos = TipoExibicao

    titulos = {
        1: ['Tipo Operação',
            'Recinto',
            'Ano',
            'Número doc.',
            'CE Mercante',
            'Data',
            'Último Evento'],
        2: ['Data',
            'Tipo Operação',
            'CE Mercante',
            'Observações',
            'Criador',
            'Último Evento',
            'Usuário'],
    }

    def __init__(self, tipo: TipoExibicao):
        self.tipo = tipo

    def get_titulos(self):
        return ExibicaoOVR.titulos[self.tipo.value]
