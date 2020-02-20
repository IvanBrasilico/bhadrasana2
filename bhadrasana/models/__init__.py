import datetime

from ajna_commons.flask.log import logger


def handle_datahora(params):
    data = params.get('adata', '')
    hora = params.get('ahora', '')
    try:
        if isinstance(data, str):
            data = datetime.datetime.strptime(data, '%Y-%m-%d')
    except Exception as err:
        data = datetime.date.today()
        logger.error('handle_datahora: %s' % err)
    try:
        if isinstance(hora, str):
            hora = datetime.datetime.strptime(hora, '%H:%M').time()
    except Exception as err:
        hora = datetime.datetime.now().time()
        logger.error('handle_datahora: %s' % err)
    return datetime.datetime.combine(data, hora)
