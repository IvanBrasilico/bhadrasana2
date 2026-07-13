from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.sqltypes import (
    Integer, BigInteger, SmallInteger, Boolean, Float, Numeric, DECIMAL,
    DateTime, Date, Text, CHAR, VARCHAR, String, TIMESTAMP
)

from bhadrasana.models.rvf import Base


def impala_type(col):
    t = col.type

    if isinstance(t, (Integer, SmallInteger)):
        return "INT"
    if isinstance(t, BigInteger):
        return "BIGINT"
    if isinstance(t, Boolean):
        return "BOOLEAN"
    if isinstance(t, (Float,)):
        return "DOUBLE"
    if isinstance(t, (Numeric, DECIMAL)):
        p = getattr(t, "precision", None) or 18
        s = getattr(t, "scale", None) or 0
        return f"DECIMAL({p},{s})"
    if isinstance(t, (DateTime, TIMESTAMP)):
        return "TIMESTAMP"
    if isinstance(t, Date):
        return "DATE"
    if isinstance(t, (Text, CHAR, VARCHAR, String)):
        return "STRING"
    return "STRING"


def sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return "'" + value.strftime("%Y-%m-%d %H:%M:%S") + "'"
    if isinstance(value, date):
        return "'" + value.strftime("%Y-%m-%d") + "'"
    s = str(value).replace("\\", "\\\\").replace("'", "''")
    return f"'{s}'"


def table_columns(table):
    return [c.name for c in table.columns]


def generate_create_table(table, schema=None):
    cols = []
    for col in table.columns:
        col_parts = [f"`{col.name}`", impala_type(col)]
        if not col.nullable:
            col_parts.append("NOT NULL")
        cols.append("  " + " ".join(col_parts))

    full_name = f"`{table.name}`" if not schema else f"`{schema}`.`{table.name}`"
    return f"CREATE TABLE IF NOT EXISTS {full_name} (\n" + ",\n".join(cols) + "\n);\n"


def generate_inserts(session, table, schema=None, chunk_size=1000):
    cols = table_columns(table)
    full_name = f"`{table.name}`" if not schema else f"`{schema}`.`{table.name}`"

    rows = session.execute(table.select()).mappings().all()
    if not rows:
        return ""

    stmts = []
    for row in rows:
        values = [sql_literal(row.get(c)) for c in cols]
        stmts.append(
            f"INSERT INTO {full_name} ({', '.join(f'`{c}`' for c in cols)}) VALUES ({', '.join(values)});"
        )
    return "\n".join(stmts) + "\n"


def export_model_to_sql(engine, base_metadata, output_file="export_impala.sql", schema=None):

    Session = sessionmaker(bind=engine)
    session = Session()

    sql_parts = []
    for table_name, table in base_metadata.tables.items():
        if table_name in EXCLUDED_TABLES:
            continue
        print(f'Gerando CREATE TABLE "{table_name}"')
        sql_parts.append(generate_create_table(table, schema=schema))

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_parts))

    for table_name, table in base_metadata.tables.items():
        if table_name in EXCLUDED_TABLES:
            continue
        print(f'Gerando INSERT "{table_name}"')
        sql_parts.append(generate_inserts(session, table, schema=schema))

    with open(f'{output_file[:-4]}_inserts.sql', "w", encoding="utf-8") as f:
        f.write("\n".join(sql_parts))

    session.close()
    return output_file


if __name__ == "__main__":
    import sys

    sys.path.append('.')
    sys.path.append('../ajna_docs/commons')
    sys.path.append('../virasana')
    from ajna_commons.flask.conf import SQL_URI

    engine = create_engine(SQL_URI)
    EXCLUDED_TABLES = (
    'ovr_imagensrvf',
    'ovr_visualizacoes',
    '',
    )

    export_model_to_sql(engine, Base.metadata, output_file="impala_dump.sql")
