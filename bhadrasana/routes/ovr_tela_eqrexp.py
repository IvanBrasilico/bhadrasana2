# ovr_tela_eqrexp.py
from flask import render_template
from sqlalchemy import text
import logging
from collections import Counter

# (opcional) se seu layout usa CSRF em formulários, podemos passar o token pro template
try:
    from flask_wtf.csrf import generate_csrf
except Exception:
    generate_csrf = None

def configure(app):
    """
    Registra as rotas da tela EQREXP.
    Requer app.config['db_session'] apontando para a sessão SQLAlchemy.
    """

    app.logger.setLevel(logging.DEBUG)

    def _get_session():
        """
        Retorna a sessão SQLAlchemy usada no app.
        Prioriza 'dbsession' (padrão do projeto) e faz fallback para 'db_session'.
        """
        s = app.config.get('dbsession')
        if s is None:
            s = app.config.get('db_session')
        if s is None:
            app.logger.error("Sessão não configurada: defina app.config['dbsession'] (ou 'db_session').")
            raise RuntimeError("dbsession não configurada")
        return s

    @app.route('/tela_eqrexp', methods=['GET'], endpoint='ovr.tela_eqrexp', strict_slashes=False)
    def tela_eqrexp():
        """
        Mostra as linhas mais recentes de ovr_ovrs
        com as colunas: id, recinto_id, create_date.
        """
        session = app.config.get('dbsession') or app.config.get('db_session')

        sql = text("""
            SELECT
              o.id,
              o.recinto_id,
              r.nome AS recinto_nome,
              COALESCE(u.nome, '-') AS responsavel_nome,
              s.nome AS setor_criador_nome,
              o.create_date,
              EXISTS (
                SELECT 1
                  FROM ovr_flags_ovr ofo
                 WHERE ofo.rvf_id = o.id
                   AND ofo.flag_id = 1
              ) AS perecivel
              ,
              EXISTS (
                SELECT 1
                  FROM ovr_eventos ev
                 WHERE ev.ovr_id = o.id
                   AND ev.tipoevento_id = 22
              ) AS verificacao_fisica_informada
            FROM ovr_ovrs o
            LEFT JOIN ovr_recintos r
                   ON r.id = o.recinto_id
            LEFT JOIN ovr_usuarios u
                   ON u.cpf = o.responsavel_cpf
            LEFT JOIN ovr_usuarios uc
                   ON uc.cpf = o.user_name
            LEFT JOIN ovr_setores s
                   ON s.id = uc.setor_id
            WHERE (fase=0 OR fase=1 OR fase=2) -- iniciada, ativa, suspensa
            AND o.setor_id = '3'            
            ORDER BY o.create_date DESC, o.id DESC
            LIMIT 200
        """)
        rows = session.execute(sql).mappings().all()

        # IDs dos recintos principais que devem ficar em destaque
        principais_ids = ('8', '9', '10', '11', '21', '22', '70')
        
        # Busca os nomes dos recintos principais para exibir mesmo quando houver 0 fichas
        sql_recintos = text(f"SELECT id, nome FROM ovr_recintos WHERE id IN {principais_ids}")
        recintos_db = session.execute(sql_recintos).mappings().all()
        
        id_to_nome_principal = {}
        counts_principais = {}
        for r_db in recintos_db:
            rec_id = str(r_db['id']).strip()
            nome = r_db['nome'] or rec_id
            counts_principais[nome] = 0
            id_to_nome_principal[rec_id] = nome

        # Failsafe: caso algum ID principal não esteja no banco, adicionamos ele manualmente
        for pid in principais_ids:
            if pid not in id_to_nome_principal:
                counts_principais[pid] = 0
                id_to_nome_principal[pid] = pid

        counts_outros = Counter()

        for r in rows:
            rec_id = str(r.get('recinto_id')).strip() if r.get('recinto_id') else ''
            nome = (r.get('recinto_nome') or r.get('recinto_id') or '─')
           
            if rec_id in principais_ids:
                nome_padrao = id_to_nome_principal[rec_id]
                counts_principais[nome_padrao] += 1
            else:
                counts_outros[nome] += 1

        agrupados_principais = sorted(counts_principais.items(), key=lambda kv: (-kv[1], kv[0]))
        agrupados_outros = sorted(counts_outros.items(), key=lambda kv: (-kv[1], kv[0]))

        return render_template(
            'tela_eqrexp.html',
            rows=rows,
            total_rows=len(rows),
            agrupados_principais=agrupados_principais,
            agrupados_outros=agrupados_outros,
            csrf_token=generate_csrf if generate_csrf else None
        )
