import os
import sys
from werkzeug.middleware.dispatcher import DispatcherMiddleware

sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

os.environ['SQL_URI'] = os.environ['SQL_URI_HOM']
# os.environ['MONGODB_URI'] = os.environ['MONGODB_URI_HOM']
os.environ['MONGODB_RISCO'] = os.environ['MONGODB_URI_HOM']
os.environ['SESSION_COOKIE'] = os.environ['SESSION_COOKIE_HOM']
print(os.environ['MONGODB_URI'])
print(os.environ['MONGODB_RISCO'])
print(os.environ['SESSION_COOKIE'])

from bhadrasana.main import app

application = DispatcherMiddleware(app,
                                   {
                                       '/bhadrasana2_hom': app
                                   })
