from sqlalchemy_schemadisplay import create_schema_graph
import sys
sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')
from bhadrasana.models.ovr import metadata

filename = 'mymodel.png'
create_schema_graph(metadata).write(filename)
