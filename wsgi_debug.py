import os
import sys
from werkzeug.serving import run_simple
from werkzeug.wsgi import DispatcherMiddleware

sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')
from ajna_commons.flask.conf import BHADRASANA_URL

os.environ['DEBUG'] = '1'
from bhadrasana.main import app




if __name__ == '__main__':
    print('Iniciando Servidor Bhadrasana 2...')
    port = 5005
    application = DispatcherMiddleware(app,
                                    {
                                        '/bhadrasana2': app
                                    })
    run_simple('localhost', port, application, use_reloader=True)
