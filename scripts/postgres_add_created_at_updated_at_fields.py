import logging

from tourmap.resources import metadata as app_metadata
from tourmap.app import app
from tourmap.resources import db

# need to import to register tables with SQLAlchemy
import tourmap.models  # pylint: disable=unused-import

import sqlalchemy as sqla
import sqlalchemy.exc
from sqlalchemy.schema import Table, MetaData

logger = logging.getLogger(__name__)

def get_engine_from_app():
    with app.app_context():
        return db.get_engine()


def app_table_names():
    return list(app_metadata.tables.keys())

def main():
    """
    A hacki'sh scrip to create created_at and updated_at columns
    on tables that do not have these yet. Add a trigger to update
    updated_at after a change.
    """
    logger.info("Start")

    engine = get_engine_from_app()
    meta = MetaData()

    # Introspect the DB
    for table_name in app_table_names():
        table = Table(table_name, meta, autoload=True, autoload_with=engine)
        logger.info("Loaded table %s", table_name)

    # The columns to be created.
    created_at_column = sqla.Column("created_at", sqla.DateTime,
                                    server_default="(now() AT TIME ZONE 'utc')")
    updated_at_column = sqla.Column("updated_at", sqla.DateTime,
                                    server_default="(now() AT TIME ZONE 'utc')")

    for table_name, table in meta.tables.items():
        add_column_if_not_exists(engine, table, created_at_column)
        add_column_if_not_exists(engine, table, updated_at_column,
                                 format_trigger=_set_current_time_on_update)


def _set_current_time_on_update(table, column):
    """
    Trigger function that will be used.
    """
    function_name = "set_{}_to_now".format(column.name)
    template = """
        CREATE OR REPLACE FUNCTION {function_name}()
        RETURNS TRIGGER AS $$
        BEGIN
            IF row(NEW.*) IS DISTINCT FROM row(OLD.*) THEN
                NEW.{column.name}=(now() AT TIME ZONE 'utc');
            END IF;
            RETURN NEW;
        END;
        $$ language 'plpgsql';

        CREATE TRIGGER update_{table.name}_{column.name}
            BEFORE UPDATE ON {table.name}
            FOR EACH ROW EXECUTE PROCEDURE {function_name}();
    """
    return template.format(table=table, column=column, function_name=function_name)


def add_column_if_not_exists(engine, table, column, format_trigger=None):
    if column.name in table.columns:
        logger.info("Table '%s' has '%s' already", table.name, column.name)
        return

    column_compiled = column.compile(dialect=engine.dialect)
    type_compiled = column.type.compile(dialect=engine.dialect)
    stmt = "ALTER TABLE {} ADD COLUMN {} {}".format(
        table.name, str(column_compiled), str(type_compiled)
    )
    if column.server_default:
        stmt = "{} DEFAULT {}".format(stmt, column.server_default.arg)

    # Adding the new column
    engine.execute(stmt)

    # Adding a trigger if required...
    if format_trigger is not None:
        trigger_script = format_trigger(table, column)
        try:
            engine.execute(trigger_script)
        except Exception as e:
            logger.error("Trigger script failed (%s)\n%s", e, trigger_script)
            stmt = "ALTER TABLE {} DROP COLUMN {}".format(
                table.name, str(column_compiled)
            )
            logger.info("Removing column!")
            engine.execute(stmt)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
