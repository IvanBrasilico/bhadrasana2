import os
import sys
from werkzeug.wsgi import DispatcherMiddleware

sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

from bhadrasana.main import app

application = DispatcherMiddleware(app,
                                   {
                                       '/bhadrasana2': app
                                   })
