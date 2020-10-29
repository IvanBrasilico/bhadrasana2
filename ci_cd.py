import sys
from fabric import Connection

msg = 'Rodou {0.command!r} em {0.connection.host}. stdout:\n{0.stdout}\n stderr:\n{0.stderr} '

if len(sys.argv) > 1 and sys.argv[1] == 'deploy':
    diretorio = '/home/ivan/ajna/bhadrasana2/'
    venv = 'bhadrasana-venv/bin/activate'
    servico = 'bhadrasana2'
else:
    diretorio = '/home/ivan/ajna/bhadrasana2_hom/'
    venv = 'bhadrasanahom-venv/bin/activate'
    servico = 'bhadrasana2_hom'

c = Connection('ajna.labin.rf08.srf')
result = c.run('cd {} && git pull'.format(diretorio))
if not result.ok:
    sys.exit('git pull falhou...')
result = c.run('cd {} && source {} && tox'.format(diretorio, venv))
#print(msg.format(result))
if result.ok:
    c.run('supervisorctl restart {}'.format(servico), pty=True)
