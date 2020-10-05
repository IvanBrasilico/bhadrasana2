import sys
from werkzeug.middleware.dispatcher import DispatcherMiddleware

sys.path.append('../ajna_docs/commons')
sys.path.append('../ajna_api')
sys.path.append('../virasana')

from bhadrasana.main import app

application = DispatcherMiddleware(app,
                                   {
                                       '/bhadrasana2': app
                                   })
