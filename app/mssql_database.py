"""
MSSQL Database Connection — Separate SQLAlchemy engine for SQL Server.

This connects to the [Salesy] database on SQL Server, which hosts the
AiCallTracking table.  The existing SQLite setup (database.py) remains
untouched; this is an independent connection.

Pre-requisites:
    pip install pyodbc
    ODBC Driver 18 for SQL Server installed on the host OS
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import urllib.parse
import os
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Read individual SQL Server env vars                                 #
# ------------------------------------------------------------------ #
SQL_SERVER = os.getenv("SQL_SERVER", "")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Salesy")
SQL_USER = os.getenv("SQL_USER", "")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")
SQL_DRIVER = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
SQL_ENCRYPT = os.getenv("SQL_ENCRYPT", "yes")
SQL_TRUST_SERVER_CERTIFICATE = os.getenv("SQL_TRUST_SERVER_CERTIFICATE", "yes")

if not SQL_SERVER or not SQL_USER:
    logger.warning(
        "⚠️  SQL Server credentials not fully set in .env — "
        "AiCallTracking endpoints will not work until configured."
    )

# Build the pyodbc connection string via odbc_connect parameter
# This handles special characters in the password safely
_odbc_params = urllib.parse.quote_plus(
    f"DRIVER={{{SQL_DRIVER}}};"
    f"SERVER={SQL_SERVER};"
    f"DATABASE={SQL_DATABASE};"
    f"UID={SQL_USER};"
    f"PWD={SQL_PASSWORD};"
    f"Encrypt={SQL_ENCRYPT};"
    f"TrustServerCertificate={SQL_TRUST_SERVER_CERTIFICATE};"
)

MSSQL_CONNECTION_STRING = f"mssql+pyodbc:///?odbc_connect={_odbc_params}"

# ------------------------------------------------------------------ #
#  Engine & Session                                                    #
# ------------------------------------------------------------------ #
MssqlBase = declarative_base()

_engine = None
MssqlSessionLocal = None


def get_mssql_engine():
    """Lazy-init the SQL Server engine (created on first call)."""
    global _engine
    if _engine is None:
        if not SQL_SERVER or not SQL_USER:
            raise RuntimeError(
                "SQL Server credentials (SQL_SERVER, SQL_USER, etc.) "
                "are not configured in .env"
            )
        _engine = create_engine(
            MSSQL_CONNECTION_STRING,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        logger.info("SQL Server engine created for %s/%s", SQL_SERVER, SQL_DATABASE)
    return _engine


def get_mssql_session():
    """Get a new SQL Server session. Use as a context manager or close manually."""
    global MssqlSessionLocal
    if MssqlSessionLocal is None:
        MssqlSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_mssql_engine(),
        )
    return MssqlSessionLocal()
