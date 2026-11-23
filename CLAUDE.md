# bhadrasana2 — Fichas

## O que é este repositório

`bhadrasana2` é o módulo "Bhadrasana" do sistema AJNA (Vigilância Aduaneira), e hospeda o sistema conhecido internamente como **Fichas**: gestão de OVR/RVF (ocorrências e verificações físicas), apreensões, riscos, integrações com API Recintos, CENCOMM, assistentes de exportação/contrafação/TG, dashboards operacionais, etc.

**Fichas está em produção, em uso ativo, e em desenvolvimento incremental contínuo.** Este não é um projeto greenfield nem um protótipo — mudanças aqui afetam um sistema real em operação.

**Nome do sistema (23/10/2026):** o AJNA foi rebatizado **NAVI** — módulos **NAVI-I** (importação), **NAVI-E** (exportação) e o Fichas como **Navi-Fichas** (decidido pelo usuário). Grafia em maiúsculas, decisão do usuário. Em texto NOVO para o usuário (títulos, marcas, manual, relatórios) usar "NAVI", nunca "AJNA". O legado com "AJNA" (`layout.html`/`new_base.html`, ~37 templates daqui e ~29 do virasana, textos históricos) fica como está por enquanto, decisão do usuário: só mexer com novo pedido. Identificadores técnicos (repositórios, `ajna_commons`, `ajna_docs`, URL `/ajna/` do manual, programas do supervisor já em produção) não mudam sem pedido explícito.

**NAVI — Navegador Analítico de Vigilância Inteligente.** Os módulos, nas palavras do usuário (29/10/2026):

- **NAVI-I** — análise de risco, imagens de escaneamento e logística, com foco na importação (no `../navi-i`).
- **NAVI-E** — análise de risco, imagens de escaneamento e logística, com foco na exportação, e controle do COV.
- **Navi-Fichas** — controle do andamento das ações fiscais e controle de carga (**este repositório**).
- **NAVI-Dados** — coleção de APIs e scripts que alimentam os dados corporativos usados pelos sistemas: dados de
  sistemas externos em vários namespaces (Pucomex DUE, Mercante, API Recintos, CNPJ, CPF...); repositório `../navi-dados`.

**Padrão de todos os módulos** (usuário, 29/10/2026): testes abrangentes, com cobertura medida; boas práticas — gate
de qualidade (pytest com coverage, flake8, bandit, radon) e CI/CD (o GitLab interno não tem runner: o gate roda local e
no `tox`, no modelo do `qualidade_navii.py` do virasana); e manual do usuário em site MkDocs (`ajna_docs/docs2.0`,
publicado em `/ajna/`). Funcionalidade nova só está pronta com testes, gate e manual atualizado. Aqui o gate é o
`tox` (ver "Como rodar os testes"), comparado com a linha de base das falhas antigas.

## Stack atual

- Flask 2.3.3, Werkzeug 3.1.3, SQLAlchemy 1.4.54, pandas 2.3.3 (ver [setup.py](setup.py) — é a fonte confiável; **não confiar em [versoes.txt](versoes.txt)**, que é um dump antigo/corrompido de outro ambiente).
- Front-end: **Bootstrap + jQuery customizados** (Flask-Bootstrap, templates Jinja2 em `bhadrasana/templates`, JS em `bhadrasana/static/js`). Não é um framework SPA.
- Persistência: MySQL/SQLAlchemy (`db_session`, ORM em `bhadrasana/models`) + MongoDB (`pymongo`, usado para risco e outras coleções).
- Autenticação/sessão via `ajna_commons.flask.login` (repo irmão).
- Deploy via gunicorn (ver [Procfile](Procfile)); WSGI de produção em [wsgi_production.py](wsgi_production.py) e de homologação em [wsgi_staging.py](wsgi_staging.py).

## Dependências de repositórios irmãos

Este repo **não é autocontido** — depende de projetos irmãos no mesmo nível de diretório (referenciados via `sys.path.insert`/symlink, não via pip):

- `ajna_commons` — conf, login, logging. O código vivo está em `../ajna_docs/commons/ajna_commons` (ver [../ajna_docs/CLAUDE.md](../ajna_docs/CLAUDE.md)). A junction `bhadrasana2/ajna_commons` aponta para `../ajna_docs/ajna_commons/commons`, que não existe nesta máquina (symlink do git virou arquivo texto no Windows); o repo `../ajna_commons` separado é uma cópia de 2019, desatualizada — não usar.
- `../virasana` — integração Mercante e outras (ex.: `virasana.integracao.mercante.mercantealchemy`, usado em `tests/app_creator.py`). Tem seu próprio [CLAUDE.md](../virasana/CLAUDE.md).
- `../ajna_api` / `ajnaapi` — API Recintos (`ajnaapi.recintosapi`).

Ao investigar comportamento que não está neste repo, procurar nesses projetos irmãos antes de assumir que algo está faltando.

## Arquitetura / mapa de módulos

- `bhadrasana/main.py` — ponto de montagem da app Flask: cria `app`, conecta Mongo/SQL, registra todos os blueprints (`*_app(app)`), monta o menu de navegação (`Nav`).
- `bhadrasana/routes/` — um arquivo por blueprint/"app" (ex.: `ovr.py`, `rvf.py`, `risco.py`, `apirecintos.py`, `cencomm.py`, `lista_apreensoes.py`, `operacoes_dashboard.py`, `assistentetg.py`...). **Este é o padrão a seguir para novas "apps": um blueprint próprio em `routes/`, registrado em `main.py`.**
- `bhadrasana/models/` — modelos SQLAlchemy e managers de domínio (ex.: `ovrmanager.py`, `rvfmanager.py`, `ermodel.py`). `navii_ficha.py` (17/10/2026) abre a Ficha de repressão na importação pelo card do **NAVI-I** — era chamado pelo NAVI-I antigo do **virasana** (`virasana/navii/ficha_navii.py`, que saiu no EOL do virasana em
  09/11/2026), não tem rota no Fichas. **Hoje ninguém o chama** (só `tests/test_navii_ficha.py`): o NAVI-I novo tem a
  cópia dele e não importa o Fichas. Candidato a sair no porte do Fichas; só aditivo, usa as regras do `ovrmanager` numa transação (ver `navi-i/src/navi_i/navii/CONTEXTO.md`). **Cópia no `../navi-i`**
  (NAVI-I em repositório próprio, `navi-i/PLANO.md`, decisão 1, 03/11/2026): o NAVI-I novo terá a sua versão deste
  arquivo e de `gera_eventoovr` e `valida_mesmo_responsavel_ovr_user_name` do `ovrmanager`. Mudar essas regras aqui pede
  espelhar lá. Armadilha: o `__init__` de `BaseRastreavel` (OVR, RVF, ImagemRVF, EventoOVR) descarta os argumentos nomeados, menos `user_name` — atribuir campo a campo.
  **`laudo.Empresa` lê a `navi_cnpj`** (11/11/2026, `navi-dados/PLANO_EMPRESA_NAVI_CNPJ.md`): só leitura, sobre o
  cadastro de CNPJ do NAVI-Dados (`cnpj` de 14 dígitos é a chave; `nome` = `nome_empresarial_pj`); a `laudo_empresas`
  ficou como histórico. Um `before_flush` recusa gravar `Empresa` pelo ORM; os testes semeiam pelo Core
  (`Empresa.__table__.insert()`). CPF não procura empresa (`get_empresa` devolve `None`). Vale também para quem importa a
  classe daqui (virasana). O NAVI-I tem a mesma troca na cópia dele.
- `bhadrasana/forms/` — WTForms.
- `bhadrasana/templates/` — Jinja2, estende `layout.html`/`new_base.html` (Bootstrap).
- `bhadrasana/scripts/` — scripts de manutenção/importação standalone (ex.: `importa_tgs.py`, `exporta_para_impala_RD.py`). `fma_update.py` (rodava no cron, de hora em hora, até 10/11/2026) consulta as **FMAs eletrônicas** (Fichas de Mercadoria Abandonada, que os recintos são obrigados a informar) na API da Janela Única Portuária e abre automaticamente uma **Ficha OVR por FMA** (`tipooperacao = 0`, "Mercadoria Abandonada"; com CE, recinto, data de entrada e consignatário) para acompanhar o procedimento até a retomada pelo importador ou o perdimento. É a fonte oficial de **carga abandonada** do AJNA (útil ao ciclo de vida e ao risco, no virasana). **Cópia no NAVI-Dados**
  (09/11/2026, fase L3 do fim de vida do virasana): `navi-dados/f3/src/navi_dados/periodico/fma.py`, copiado igual.
  **Desde 10/11/2026 é ele que abre as Fichas de FMA**, de hora em hora no periódico do NAVI-Dados; o cron deste script
  foi desligado (`navi-dados/PLANO_SIVANA_FMA.md`). O script fica só como volta, até ser apagado depois de alguns dias
  estáveis. A regra da Ficha de FMA agora se muda lá.
- `bhadrasana/docx/` — geração de documentos Word a partir de modelos `.docx`.
- `bhadrasana/estudo_de_caso/` (23/11/2026) — pacote ZIP de **estudos de caso para apresentação**: dados da Ficha e
  do CE para o slide de abertura, escaneamento do contêiner, amostra das fotos da RVF em miniatura e um `SKILL.md` com
  as instruções para uma IA montar o PowerPoint (três slides por caso). Só lê. Script:
  `bhadrasana/scripts/estudo_de_caso.py` (`--ficha`, `--ano` ou nada = as 5 maiores Operações do Dashboard por Valor
  TG + Valor Multas; em cada Operação, o caso é a Ficha de maior valor). O escaneamento é achado por contêiner + data
  (a regra e os dias vão no pacote, para conferir). Lê as tabelas de portos e NCM do `../navi-i`, se estiver ao lado.
  Mudar os campos do `dados.json` pede mudar o `SKILL.md` (o teste confere os nomes). Manual: seção no
  `ajna_docs/docs2.0/docs/fichas/operacoes_dashboard.md`.
- `bhadrasana/security/check.py` — checagens de segurança/permissão.
- `tests/` — pytest; `tests/app_creator.py` monta uma app de teste com SQLite em memória + `mongomock`, e semeia usuários/setores fixos para os testes.

## Produção: prefixo `/bhadrasana2` atrás de proxy (obrigatório para código novo)

No Servidor a app roda via WSGI atrás de um **proxy Apache**, montada no prefixo **`/bhadrasana2`** por
`DispatcherMiddleware` ([wsgi_production.py](wsgi_production.py); homologação em `/bhadrasana2_hom`, [wsgi_staging.py](wsgi_staging.py)). O Apache só encaminha o
que está sob o prefixo e repassa um Host interno. Funcionar no `localhost` **não** prova que funciona
no Servidor. Regras:

- Toda URL interna sai de `url_for(...)` nos templates; o JS **recebe** as URLs do servidor
  (`var API = {{ url_for('bp.rota') | tojson }};`) e nunca monta caminhos começando com `/`.
- Sem redirect absoluto: use `redirect(url_for(...))` ou caminho relativo (padrão do código antigo,
  ex.: `redirect('bagagens?...')`). **Rotas índice com `strict_slashes=False`**: o redirect
  automático da barra final (`/tela` → `/tela/`) sai com o Host interno e quebra atrás do proxy
  (foi o caso de `/entregas_cnpj` em 01/10/2026).
- Link para a outra app usa o prefixo dela fixo: `/bhadrasana2/...` ou `/virasana/...`.
- Teste montando a app no prefixo (modelo: `tests/test_prefixo_proxy.py`, no repo `../navi-i`):
  abre cada tela com e sem barra final sem redirect e confere que todo `href`/`src`/`action`/URL do
  JS começa com o prefixo.

## Como rodar os testes

```bash
python -m pytest tests --disable-warnings
```

Nesta máquina (Windows), a junção quebrada `bhadrasana2/ajna_commons` derruba a coleta e `tests/test_api_recintos_json.py`
acessa a rede ao ser importado; use:

```bash
.bhadrasana-venv/Scripts/python.exe -m pytest tests -q --disable-warnings -p no:cacheprovider --ignore=ajna_commons --rootdir=tests --ignore=tests/test_api_recintos_json.py
```

Em 17/10/2026 a suíte já tinha 61 falhas antigas (a maioria `UNIQUE constraint failed: ovr_ovrs.id` em
`test_unitarios_ovrmanager.py`), independentes das mudanças recentes — compare com essa linha de base.

(equivalente ao `testenv` do [tox.ini](tox.ini), que também roda `coverage` e, em `testenv:check`, `flake8`/`bandit`). Os testes usam banco em memória e Mongo mockado — não tocam nas bases reais.

## Restrição principal: não arriscar produção

O usuário está adicionando novas "apps" ao sistema Fichas, mas **não** quer nenhum risco de quebrar a produção atual. Isso vale enquanto as migrações abaixo não forem explicitamente iniciadas:

- Preferir mudanças **aditivas e isoladas** (nova rota/blueprint próprio) a refatorações de código legado compartilhado.
- Evitar mexer em infraestrutura compartilhada (`main.py`, `layout.html`/`new_base.html`, `views.py`, autenticação, modelos usados pelo Fichas legado) sem necessidade explícita — e quando for necessário, tratar como mudança de maior risco e confirmar com o usuário antes.
- Não fazer upgrade de dependências centrais (Flask, Werkzeug, SQLAlchemy) como efeito colateral de outra tarefa.
- Existe ambiente de homologação separado ([wsgi_staging.py](wsgi_staging.py), variáveis `*_HOM`, montado em `/bhadrasana2_hom`) — preferir validar mudanças de maior risco por ali antes de produção.
- Rodar os testes afetados antes de considerar uma mudança pronta e oferecer a suíte completa (ver o workflow abaixo).

## Planos futuros (NÃO fazer agora, só quando solicitado explicitamente)

1. Migrar todo o sistema para versões mais novas de Flask/Python.
2. Migrar a camada de apresentação do Bootstrap+jQuery customizado atual para o **design system do governo (gov.br)**.

Essas migrações são objetivos de médio/longo prazo. Não iniciar trabalho nessa direção, nem propor mudanças "de passagem" que empurrem o código nessa direção, a menos que o usuário peça explicitamente.

## Como trabalhar neste repo (workflow)

- Para mudanças não-triviais, ou que toquem código/templates compartilhados, propor um plano antes de editar.
- Novas funcionalidades ("apps") devem ser isoladas: blueprint próprio, templates próprios, e reaproveitar models existentes só por leitura/consulta quando fizer sentido — evitar acoplar o novo código às entranhas do Fichas legado.
- Rodar `pytest` (e `flake8`/`bandit` quando pertinente) antes de dar uma tarefa como concluída — **só os testes
  necessários** (pedido do usuário, 22/10/2026): numa mudança localizada, os arquivos de teste da área
  (`pytest tests/test_x.py ...`), não a suíte inteira. Ao terminar, dizer o que rodou e **oferecer** a suíte
  completa — não rodar sem o usuário aceitar, salvo mudança ampla ou em código compartilhado. Mudança no que o
  virasana importa daqui (os modelos das telas Bagagens e API Recintos: `bhadrasana/models/apirecintos.py`,
  `apirecintos_risco.py`, `ovr.py`, `rvf.py`, `laudo.py`, `ovrmanager.get_recintos_api`) pode quebrar o virasana, que
  está em fim de vida e sem gate: conferir que ele sobe e que `/virasana/bagagens` e `/virasana/eventos` respondem
  (ver o `CLAUDE.md` de lá).
