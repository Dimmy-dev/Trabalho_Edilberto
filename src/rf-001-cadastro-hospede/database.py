import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Tenta carregar URL do MySQL configurada; se indisponível ou inacessível no teste, usa SQLite local resiliente
MYSQL_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:root@localhost:3306/db_hotel_grand_plaza")
FALLBACK_SQLITE_URL = "sqlite:///./hotel_grand_plaza.db"

try:
    # Teste de conexão com o banco preferencial
    if "mysql" in MYSQL_URL:
        # Tenta criar o engine do MySQL com timeout curto de teste
        test_engine = create_engine(MYSQL_URL, pool_pre_ping=True, connect_args={"connect_timeout": 2})
        with test_engine.connect():
            DATABASE_URL = MYSQL_URL
            engine = test_engine
    else:
        DATABASE_URL = MYSQL_URL
        engine = create_engine(DATABASE_URL)
except Exception:
    # Fallback seguro para manter a aplicação funcional e auditável de imediato
    DATABASE_URL = FALLBACK_SQLITE_URL
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
