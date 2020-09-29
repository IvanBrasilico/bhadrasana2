"""Um script simples para adicionar um usuário ao BD.

Uso:
   python ajna_commons/scripts/adduser.py -u=username -p=password

"""
import click

from ajna_commons.flask.user import DBUser
from bhadrasana.models import db_session, Usuario


@click.command()
@click.option('-u', help='Nome de usuário', prompt='Digite o nome de usuário')
@click.option('-p', help='Senha', prompt='Agora digite a senha')
def adduser(u, p):
    """Insere usuário no Banco de Dados ou atualiza senha."""
    DBUser.dbsession = db_session
    DBUser.alchemy_class = Usuario
    return DBUser.add(u, p)


if __name__ == '__main__':
    print(adduser())
