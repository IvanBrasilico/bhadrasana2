import sys
import unittest

#from flask_testing import TestCase
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append('.')

import ajna_commons.flask.login as login_ajna
from ajna_commons.flask.user import DBUser
from bhadrasana.models.ovr import metadata
from bhadrasana.views import app

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
metadata.create_all(engine)

SECRET = 'teste'


def configure_app(app, sqlsession):
    """Configurações gerais e de Banco de Dados da Aplicação."""
    app.config['DEBUG'] = False
    app.secret_key = SECRET
    app.config['SECRET_KEY'] = SECRET
    app.config['SESSION_TYPE'] = 'filesystem'
    login_ajna.configure(app)
    DBUser.dbsession = None
    app.config['dbsession'] = sqlsession
    return app


class OVRTestCase(unittest.TestCase):

    def setUp(self) -> None:
        configure_app(app, session)
        self.app = app.test_client()

    def tearDown(self) -> None:
        pass

    def test_home(self):
        self.app.get('/')


if __name__ == '__main__':
    unittest.main()
