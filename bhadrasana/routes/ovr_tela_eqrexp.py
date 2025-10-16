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
        Mostra as 50 linhas mais recentes de ovr_ovrs
        com as colunas: id, recinto_id, create_date.
        """
        session = _get_session()

        sql = text("""
            SELECT id, recinto_id, create_date
            FROM ovr_ovrs
            ORDER BY create_date DESC, id DESC
            LIMIT 50
        """)
        rows = session.execute(sql).mappings().all()

        return render_template(
            'tela_eqrexp.html',
            rows=rows,
            csrf_token=generate_csrf if generate_csrf else None
        )
