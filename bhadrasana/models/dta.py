from sqlalchemy import BigInteger, Column, VARCHAR, Boolean, Integer
from sqlalchemy import ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()
metadata = Base.metadata

tipoConteudo = [
    'Nada',
    'Fatura',
    'Planilha',
    'SoftPorn',
    'Mangá'
]


class Enumerado:

    @classmethod
    def get_tipo(cls, listatipo: list, id: int = None):
        if (id is not None) and isinstance(id, int):
            return listatipo[id]
        else:
            return [(id, item) for id, item in enumerate(listatipo)]

    @classmethod
    def tipoConteudo(cls, id=None):
        return cls.get_tipo(tipoConteudo, id)


class DTA(Base):
    __tablename__ = 'dta_dtas'
    id = Column(BigInteger(), primary_key=True)
    numero = Column(VARCHAR(10), index=True, nullable=False)
    anexos = relationship("Anexo", back_populates="dta")


class Anexo(Base):
    __tablename__ = 'dta_anexos'
    id = Column(BigInteger(), primary_key=True)
    dta_id = Column(BigInteger(), ForeignKey('dta_dtas.id'))
    dta = relationship("DTA", back_populates="anexos")
    nomearquivo = Column(VARCHAR(200), index=True, nullable=False)
    observacoes = Column(VARCHAR(200), index=True, nullable=False)
    temconteudo = Column(Boolean(), index=True)
    qualidade = Column(Integer(), index=True)
    tipoconteudo = Column(Integer(), index=True)

    def get_tipoconteudo(self):
        return Enumerado.tipoConteudo(self.unidadedemedida)


if __name__ == '__main__':
    import sys

    sys.path.insert(0, '.')
    sys.path.insert(0, '../ajna_docs/commons')
    sys.path.insert(0, '../virasana')
    from bhadrasana.main import engine

    metadata.create_all(engine,
                        [
                            metadata.tables['dta_dtas'],
                            metadata.tables['dta_anexos'],
                        ])
