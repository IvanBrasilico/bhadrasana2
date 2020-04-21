import os
import sys
from werkzeug.wsgi import DispatcherMiddleware

sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

os.environ['SQL_URI'] = os.environ['SQL_URI_HOM']
from bhadrasana.main import app

application = DispatcherMiddleware(app,
                                   {
                                       '/bhadrasana2_hom': app
                                   })
