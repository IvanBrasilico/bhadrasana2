from datetime import date, datetime, timedelta

today = date.today()
str_today = datetime.strftime(today, '%d/%m/%Y')
yesterday = today - timedelta(days=1)
str_yesterday = datetime.strftime(yesterday, '%d/%m/%Y')


def parse_datas(inicio, fim):
    return datetime.strptime(inicio, '%d/%m/%Y'), \
           datetime.strptime(fim + ' 23:59:59', '%d/%m/%Y %H:%M:%S')
