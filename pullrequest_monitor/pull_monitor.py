import cx_Oracle
from sqlalchemy.orm import sessionmaker
import dto_requests_objects as dto
from sqlalchemy import create_engine
import logging
import json
import github_walker


github_logger = logging.getLogger("github_monitor")

CONNECTIONS_CONFIG = "config/connections_config_local.json"
GITHUB_LOADER_CONFIG = "config/github_monitor_config.json"

with open(CONNECTIONS_CONFIG) as f:
    conn_cfg = json.load(f)

with open(GITHUB_LOADER_CONFIG) as f:
    loader_cfg = json.load(f)


def ora_connect():
    host = conn_cfg["db"]["host"]
    port = conn_cfg["db"]["port"]
    database = conn_cfg["db"]["service"]
    username = conn_cfg["db"]["username"]
    password = conn_cfg["db"]["password"]

    drop_tables = loader_cfg["drop_tables"]

    dsnstr = cx_Oracle.makedsn(host, port, database).replace("SID", "SERVICE_NAME")
    cstr = 'oracle+cx_oracle://{username}:{password}@{dsnstr}'.format(
        username=username,
        password=password,
        dsnstr=dsnstr
    )
    engine = create_engine(
        cstr,
        convert_unicode=False,
        pool_recycle=10,
        pool_size=50,
        echo=False if loader_cfg["dml_echo"] == "N" else True
    )
    if drop_tables == "Y":
        dto.Base.metadata.drop_all(bind=engine, checkfirst=True)
        dto.Base.metadata.create_all(bind=engine, checkfirst=True)

    db_session = sessionmaker(bind=engine)
    session = db_session()
    return session


def sqllite_connect():
    engine = create_engine('sqlite:///git_pullrequests.db')
    db_session = sessionmaker(bind=engine)
    session = db_session()

    if loader_cfg["drop_tables"] == "Y":
        dto.Base.metadata.drop_all(bind=engine, checkfirst=True)
        dto.Base.metadata.create_all(bind=engine, checkfirst=True)

    return session


def main():
    github_logger.setLevel(loader_cfg["log_level"])

    if loader_cfg["db_provider"] == "Oracle":
        db_session = ora_connect()
    else:
        db_session = sqllite_connect()

    if db_session is not None:
        ghw = github_walker.GitHubWalker(db_session, loader=GITHUB_LOADER_CONFIG, connections=CONNECTIONS_CONFIG)
        ghw.repository_walk()
        ghw.pull_requests_walk()
        ghw.ghl.dump_to_file("analysis/python/raw")

    db_session.close()


if __name__ == "__main__":
    main()
