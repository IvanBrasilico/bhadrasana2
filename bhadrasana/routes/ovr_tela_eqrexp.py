# ovr_tela_eqrexp.py
from flask import render_template
from sqlalchemy import text
import logging

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
            FROM ovr_ovrs o
            LEFT JOIN ovr_recintos r
                   ON r.id = o.recinto_id
            LEFT JOIN ovr_usuarios u
                   ON u.cpf = o.responsavel_cpf
            WHERE tipooperacao=2 -- exportação
            ORDER BY o.create_date DESC, o.id DESC
            LIMIT 100
        """)
        rows = session.execute(sql).mappings().all()

        return render_template(
            'tela_eqrexp.html',
            rows=rows,
            csrf_token=generate_csrf if generate_csrf else None
        )
