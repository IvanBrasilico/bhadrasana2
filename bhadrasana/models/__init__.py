import datetime


def handle_datahora(params):
    data = params.get('adata', '')
    hora = params.get('ahora', '')
    try:
        if isinstance(data, str):
            data = datetime.strptime(data, '%Y-%m-%d')
    except:
        data = datetime.date.today()
    try:
        if isinstance(hora, str):
            hora = datetime.strptime(data, '%H:%M')
    except:
        hora = datetime.datetime.now().time()
    return datetime.datetime.combine(data, hora)
