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
            WHERE (fase=0 OR fase=1 OR fase=2) -- iniciada, ativa, suspensa
            AND o.setor_id = '3'            
            ORDER BY o.create_date DESC, o.id DESC
            LIMIT 200
        """)
        rows = session.execute(sql).mappings().all()

        # Agrupa por recinto (nome se houver, senão id, senão ─)
        counts = Counter()
        for r in rows:
            nome = (r.get('recinto_nome') or r.get('recinto_id') or '─')
            counts[nome] += 1
        agrupados_por_recinto = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

        return render_template(
            'tela_eqrexp.html',
            rows=rows,
            total_rows=len(rows),
            agrupados_por_recinto=agrupados_por_recinto,
            csrf_token=generate_csrf if generate_csrf else None
        )
