# bhadrasana2 — Fichas

## O que é este repositório

`bhadrasana2` é o módulo "Bhadrasana" do sistema AJNA (Vigilância Aduaneira), e hospeda o sistema conhecido internamente como **Fichas**: gestão de OVR/RVF (ocorrências e verificações físicas), apreensões, riscos, integrações com API Recintos, CENCOMM, assistentes de exportação/contrafação/TG, dashboards operacionais, etc.

**Fichas está em produção, em uso ativo, e em desenvolvimento incremental contínuo.** Este não é um projeto greenfield nem um protótipo — mudanças aqui afetam um sistema real em operação.

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
- `bhadrasana/models/` — modelos SQLAlchemy e managers de domínio (ex.: `ovrmanager.py`, `rvfmanager.py`, `ermodel.py`).
- `bhadrasana/forms/` — WTForms.
- `bhadrasana/templates/` — Jinja2, estende `layout.html`/`new_base.html` (Bootstrap).
- `bhadrasana/scripts/` — scripts de manutenção/importação standalone (ex.: `importa_tgs.py`, `exporta_para_impala_RD.py`).
- `bhadrasana/docx/` — geração de documentos Word a partir de modelos `.docx`.
- `bhadrasana/security/check.py` — checagens de segurança/permissão.
- `tests/` — pytest; `tests/app_creator.py` monta uma app de teste com SQLite em memória + `mongomock`, e semeia usuários/setores fixos para os testes.

## Como rodar os testes

```bash
python -m pytest tests --disable-warnings
```

(equivalente ao `testenv` do [tox.ini](tox.ini), que também roda `coverage` e, em `testenv:check`, `flake8`/`bandit`). Os testes usam banco em memória e Mongo mockado — não tocam nas bases reais.

## Restrição principal: não arriscar produção

O usuário está adicionando novas "apps" ao sistema Fichas, mas **não** quer nenhum risco de quebrar a produção atual. Isso vale enquanto as migrações abaixo não forem explicitamente iniciadas:

- Preferir mudanças **aditivas e isoladas** (nova rota/blueprint próprio) a refatorações de código legado compartilhado.
- Evitar mexer em infraestrutura compartilhada (`main.py`, `layout.html`/`new_base.html`, `views.py`, autenticação, modelos usados pelo Fichas legado) sem necessidade explícita — e quando for necessário, tratar como mudança de maior risco e confirmar com o usuário antes.
- Não fazer upgrade de dependências centrais (Flask, Werkzeug, SQLAlchemy) como efeito colateral de outra tarefa.
- Existe ambiente de homologação separado ([wsgi_staging.py](wsgi_staging.py), variáveis `*_HOM`, montado em `/bhadrasana2_hom`) — preferir validar mudanças de maior risco por ali antes de produção.
- Rodar a suíte de testes antes de considerar uma mudança pronta.

## Planos futuros (NÃO fazer agora, só quando solicitado explicitamente)

1. Migrar todo o sistema para versões mais novas de Flask/Python.
2. Migrar a camada de apresentação do Bootstrap+jQuery customizado atual para o **design system do governo (gov.br)**.

Essas migrações são objetivos de médio/longo prazo. Não iniciar trabalho nessa direção, nem propor mudanças "de passagem" que empurrem o código nessa direção, a menos que o usuário peça explicitamente.

## Como trabalhar neste repo (workflow)

- Para mudanças não-triviais, ou que toquem código/templates compartilhados, propor um plano antes de editar.
- Novas funcionalidades ("apps") devem ser isoladas: blueprint próprio, templates próprios, e reaproveitar models existentes só por leitura/consulta quando fizer sentido — evitar acoplar o novo código às entranhas do Fichas legado.
- Rodar `pytest` (e `flake8`/`bandit` quando pertinente) antes de dar uma tarefa como concluída.
