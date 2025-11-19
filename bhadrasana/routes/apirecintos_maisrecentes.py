# apirecintos_maisrecentes.py
from flask import jsonify
from sqlalchemy import text
import logging


def configure(app):
    """
    Registra o endpoint /apirecintos/maisrecentes.

    Por enquanto, este endpoint retorna apenas a dataHoraOcorrencia
    mais recente para o codigoRecinto = '8932788'.

    Requer:
    - app.config['dbsession'] ou app.config['db_session']
      apontando para a sessão SQLAlchemy.
    """

    # Deixa o logger em DEBUG, como no padrão do projeto
    app.logger.setLevel(logging.DEBUG)

    def _get_session():
        """
        Retorna a sessão SQLAlchemy usada no app.

        Prioriza 'dbsession' (padrão do projeto) e faz fallback para 'db_session'.
        Levanta RuntimeError se nada estiver configurado.
        """
        s = app.config.get('dbsession')
        if s is None:
            s = app.config.get('db_session')
        if s is None:
            app.logger.error(
                "Sessão não configurada: defina app.config['dbsession'] "
                "ou app.config['db_session']."
            )
            raise RuntimeError("dbsession não configurada")
        return s

    @app.route(
        '/apirecintos/maisrecentes',
        methods=['GET'],
        endpoint='api.apirecintos_maisrecentes',
        strict_slashes=False
    )
    def apirecintos_maisrecentes():
        """
        Retorna a dataHoraOcorrencia mais recente
        para o codigoRecinto fixo '8932788'.

        Exemplo de resposta (JSON):

        {
          "codigoRecinto": "8932788",
          "max_dataHoraOcorrencia": "2025-11-19 13:42:00",
          "found": true
        }
        """
        session = _get_session()

        # Consulta simples usando o índice em (codigoRecinto, dataHoraOcorrencia)
        sql = text("""
            SELECT
                MAX(dataHoraOcorrencia) AS max_dataHoraOcorrencia
            FROM apirecintos_acessosveiculo
            WHERE codigoRecinto = :codigoRecinto
        """)

        params = {"codigoRecinto": "8932788"}

        # Usamos .mappings().first() para obter um dict-like
        result = session.execute(sql, params).mappings().first()
        max_dt = result["max_dataHoraOcorrencia"] if result else None

        # Log auxiliar para depuração
        app.logger.debug(
            "apirecintos_maisrecentes: codigoRecinto=%s, max_dataHoraOcorrencia=%s",
            params["codigoRecinto"],
            max_dt,
        )

        if max_dt is None:
            # Nenhum registro encontrado para o recinto
            payload = {
                "codigoRecinto": params["codigoRecinto"],
                "max_dataHoraOcorrencia": None,
                "found": False,
            }
        else:
            # Convertendo datetime para string (formato amigável)
            payload = {
                "codigoRecinto": params["codigoRecinto"],
                "max_dataHoraOcorrencia": max_dt.isoformat(sep=' ', timespec='seconds'),
                "found": True,
            }

        # jsonify garante Content-Type application/json
        return jsonify(payload)
