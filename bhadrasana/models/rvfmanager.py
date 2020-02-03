from bhadrasana.models.rvf import Marca, RVF


def get_marcas(session):
    marcas = session.query(Marca).all()
    return [marca for marca in marcas]

def get_rvf(session, id):
    return session.query(RVF).filter(RVF.id == id).one_or_none()

def cadastra_rvf(session,
                 id,
                 descricao,
                 numeroCEmercante):
    if id:
        rvf = session.query(RVF).filter(RVF.id == id).one_or_none()
    else:
        rvf = RVF()
    rvf.descricao = descricao
    rvf.numeroCEmercante = numeroCEmercante
    session.add(rvf)
    session.commit()
    return rvf


def gerencia_marca_encontrada(session, rvf_id, marca_id, inclui=True):
    rvf = session.query(RVF).filter(RVF.id == rvf_id).one_or_none()
    if rvf:
        marca = session.query(Marca).filter(Marca.id == marca_id).one_or_none()
        if marca:
            if inclui:
                print('Incluindo MARCA...', marca)
                rvf.marcasencontradas.append(marca)
            else:
                rvf.marcasencontradas.remove(marca)
            session.commit()
            return rvf.marcasencontradas
    return None


def inclui_marca_encontrada(session, rvf_id, marca_nome):
    marca = session.query(Marca).filter(Marca.nome == marca_nome).one_or_none()
    if marca:
        return gerencia_marca_encontrada(session, rvf_id, marca.id, inclui=True)
    return None


def exclui_marca_encontrada(session, rvf_id, marca_id):
    return gerencia_marca_encontrada(session, rvf_id, marca_id, inclui=False)
