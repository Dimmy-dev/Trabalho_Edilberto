"""
PROVEDOR DE CONEXÃO E PERSISTÊNCIA DUAL-MODE RESILIENTE
Grand Plaza Hotel Management System — Core Unificado (RF-001 a RF-005)
Diretrizes: regras/back.md e regras/DB.md

Prioridade de Conexão:
1. Supabase Cloud PostgreSQL 15+ (quando DATABASE_URL estiver disponível e acessível).
2. Fallback transparente para SQLite local (hotel_grand_plaza.db) para homologação offline.
"""

import os
import sys
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

try:
    from dotenv import load_dotenv
    # Carrega variáveis de ambiente do .env da raiz do projeto ou local
    env_raiz = Path(__file__).resolve().parent.parent / ".env"
    if env_raiz.exists():
        load_dotenv(dotenv_path=env_raiz)
    else:
        env_local = Path(__file__).resolve().parent / ".env"
        if env_local.exists():
            load_dotenv(dotenv_path=env_local)
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GrandPlazaDB-Core")

Base = declarative_base()

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE_PATH = CURRENT_DIR / "hotel_grand_plaza.db"

# Se o banco local do core não existir, herda o banco populado do RF-005
if not DB_FILE_PATH.exists():
    db_rf5 = PROJECT_ROOT / "rf-005-consumo" / "hotel_grand_plaza.db"
    if db_rf5.exists():
        try:
            import shutil
            shutil.copy2(db_rf5, DB_FILE_PATH)
            logger.info("Banco SQLite inicial herdado com sucesso do RF-005.")
        except Exception as e:
            logger.warning(f"Não foi possível copiar banco inicial: {e}")

DB_DIAGNOSTICS = {
    "engine_type": "SQLite Localhost (Resiliente)",
    "supabase_connected": False,
    "error": None,
    "database_url_configured": False
}

def obter_engine():
    """Retorna a engine SQLAlchemy com conexão segura e fallback automático."""
    global DB_DIAGNOSTICS
    
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        database_url = database_url.strip()
    
    # Tentativa de conexão ao Supabase PostgreSQL se configurado
    if database_url and ("postgresql" in database_url or "postgres://" in database_url):
        DB_DIAGNOSTICS["database_url_configured"] = True
        url_formatada = database_url
        if url_formatada.startswith("postgres://"):
            url_formatada = url_formatada.replace("postgres://", "postgresql://", 1)
        if "pgbouncer=true" in url_formatada:
            url_formatada = url_formatada.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
            
        try:
            logger.info("Conectando ao banco em nuvem Supabase (PostgreSQL 15+)...")
            from sqlalchemy.pool import NullPool
            engine_cloud = create_engine(
                url_formatada,
                connect_args={"connect_timeout": 5},
                poolclass=NullPool
            )
            with engine_cloud.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Conexão com Supabase PostgreSQL confirmada com sucesso!")
            DB_DIAGNOSTICS["engine_type"] = "Supabase PostgreSQL (Nuvem)"
            DB_DIAGNOSTICS["supabase_connected"] = True
            DB_DIAGNOSTICS["error"] = None
            return engine_cloud
        except Exception as e:
            logger.warning(f"Nuvem inacessível ({e}). Ativando modo local SQLite transparente...")
            DB_DIAGNOSTICS["error"] = str(e)

    # Operação Localhost Segura e Autônoma: SQLite local
    is_serverless = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
    if is_serverless:
        sqlite_path = Path("/tmp") / "hotel_grand_plaza.db"
        if not sqlite_path.exists() and DB_FILE_PATH.exists():
            import shutil
            try:
                shutil.copy2(DB_FILE_PATH, sqlite_path)
            except Exception:
                pass
    else:
        sqlite_path = DB_FILE_PATH

    logger.info(f"Ambiente Resiliente ativo. SQLite: {sqlite_path}")
    DB_DIAGNOSTICS["engine_type"] = "SQLite Localhost (Resiliente)"
    DB_DIAGNOSTICS["supabase_connected"] = False

    sqlite_url = f"sqlite:///{sqlite_path}"
    engine_local = create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False}
    )
    return engine_local

engine = obter_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Injeção de dependência FastAPI: sessão do banco com fechamento garantido."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def garantir_dados_iniciais():
    """Popula acomodações, hóspedes, operadores, estadias e catálogo de consumo se faltarem dados."""
    from models import (
        AcomodacaoModel, HospedeModel, OperadorModel, 
        ItemServicoModel, HospedagemModel, ConsumoModel
    )
    import uuid
    import bcrypt
    from datetime import datetime, timedelta

    db = SessionLocal()
    try:
        # 1. Operadores do Sistema (RF-003)
        salt = bcrypt.gensalt(rounds=12)
        senha_hash_padrao = bcrypt.hashpw(b"Hotel@2026!", salt).decode("utf-8")
        
        operadores_iniciais = [
            {"email": "recepcao@grandplaza.com", "nome": "Maria Oliveira (Recepção)", "cargo": "RECEPCIONISTA"},
            {"email": "gerencia@grandplaza.com", "nome": "Carlos Alberto (Gerência Geral)", "cargo": "GERENTE"},
            {"email": "admin@grandplaza.com", "nome": "Administrador Master", "cargo": "ADMIN"}
        ]
        for op_info in operadores_iniciais:
            op_db = db.query(OperadorModel).filter_by(email=op_info["email"]).first()
            if not op_db:
                novo_op = OperadorModel(
                    uuid_publico=str(uuid.uuid4()),
                    nome=op_info["nome"],
                    email=op_info["email"],
                    cargo=op_info["cargo"],
                    senha_hash=senha_hash_padrao,
                    is_ativo=1
                )
                db.add(novo_op)
        db.commit()

        # 2. Quartos do Hotel (RF-004)
        if db.query(AcomodacaoModel).count() == 0:
            quartos_iniciais = [
                {"numero": "101", "categoria": "STANDARD", "capacidade": 2, "tarifa_base": 280.00, "status": "DISPONIVEL", "andar": 1, "descricao": "Quarto Standard com 1 cama de casal Queen, Wi-Fi 6 e mesa de trabalho"},
                {"numero": "102", "categoria": "STANDARD", "capacidade": 2, "tarifa_base": 280.00, "status": "DISPONIVEL", "andar": 1, "descricao": "Quarto Standard com 2 camas de solteiro e vista interna tranquila"},
                {"numero": "103", "categoria": "STANDARD", "capacidade": 3, "tarifa_base": 340.00, "status": "LIMPEZA", "andar": 1, "descricao": "Quarto Standard Triplo com 1 cama de casal e 1 de solteiro"},
                {"numero": "104", "categoria": "STANDARD", "capacidade": 1, "tarifa_base": 240.00, "status": "DISPONIVEL", "andar": 1, "descricao": "Quarto Individual Compacto ideal para viajantes corporativos"},
                {"numero": "105", "categoria": "STANDARD", "capacidade": 2, "tarifa_base": 280.00, "status": "OCUPADO", "andar": 1, "descricao": "Quarto Standard com vista para o jardim"},
                {"numero": "201", "categoria": "LUXO", "capacidade": 2, "tarifa_base": 490.00, "status": "DISPONIVEL", "andar": 2, "descricao": "Suíte Luxo com cama King Size, varanda panorâmica e hidromassagem"},
                {"numero": "202", "categoria": "LUXO", "capacidade": 2, "tarifa_base": 490.00, "status": "OCUPADO", "andar": 2, "descricao": "Suíte Luxo com isolamento acústico reforçado e cafeteira Nespresso"},
                {"numero": "203", "categoria": "LUXO", "capacidade": 4, "tarifa_base": 620.00, "status": "MANUTENCAO", "andar": 2, "descricao": "Suíte Luxo Familiar com ante-sala e 2 banheiros completos"},
                {"numero": "204", "categoria": "LUXO", "capacidade": 2, "tarifa_base": 490.00, "status": "DISPONIVEL", "andar": 2, "descricao": "Suíte Luxo Master com Smart TV 65 polegadas e adega climatizada"},
                {"numero": "301", "categoria": "PRESIDENCIAL", "capacidade": 4, "tarifa_base": 1450.00, "status": "DISPONIVEL", "andar": 3, "descricao": "Suíte Presidencial Imperial com living privativo, closet e mordomo 24h"},
                {"numero": "302", "categoria": "PRESIDENCIAL", "capacidade": 6, "tarifa_base": 2100.00, "status": "DISPONIVEL", "andar": 3, "descricao": "Cobertura Penthouse com terraço gourmet privativo e vista da orla"}
            ]
            for q in quartos_iniciais:
                acom = AcomodacaoModel(
                    uuid_publico=str(uuid.uuid4()),
                    numero=q["numero"],
                    categoria=q["categoria"],
                    capacidade=q["capacidade"],
                    tarifa_base=q["tarifa_base"],
                    status=q["status"],
                    andar=q["andar"],
                    descricao=q["descricao"],
                    is_ativo=1
                )
                db.add(acom)
            db.commit()

        # 3. Catálogo de Produtos e Frigobar (RF-005)
        if db.query(ItemServicoModel).count() == 0:
            itens_iniciais = [
                {"codigo": "FRIG-001", "nome": "Água Mineral sem Gás 500ml", "categoria": "FRIGOBAR", "preco_unitario": 6.00, "descricao": "Garrafa de água mineral natural"},
                {"codigo": "FRIG-002", "nome": "Água Mineral com Gás 500ml", "categoria": "FRIGOBAR", "preco_unitario": 6.50, "descricao": "Garrafa de água gaseificada"},
                {"codigo": "FRIG-003", "nome": "Refrigerante Coca-Cola Lata 350ml", "categoria": "FRIGOBAR", "preco_unitario": 9.00, "descricao": "Refrigerante clássico gelado"},
                {"codigo": "FRIG-004", "nome": "Cerveja Artesanal IPA 355ml", "categoria": "FRIGOBAR", "preco_unitario": 18.00, "descricao": "Cerveja puro malte premium"},
                {"codigo": "FRIG-005", "nome": "Chocolate Suíço em Barra 80g", "categoria": "FRIGOBAR", "preco_unitario": 14.50, "descricao": "Chocolate ao leite nobre"},
                {"codigo": "SERV-001", "nome": "Café da Manhã no Quarto", "categoria": "SERVICO_QUARTO", "preco_unitario": 45.00, "descricao": "Cesta completa de café e frutas"},
                {"codigo": "SERV-002", "nome": "Lavanderia Expressa (Peça)", "categoria": "LAVANDERIA", "preco_unitario": 22.00, "descricao": "Lavagem e passadoria em 4h"},
                {"codigo": "SERV-003", "nome": "Diária de Estacionamento", "categoria": "ESTACIONAMENTO", "preco_unitario": 30.00, "descricao": "Vaga coberta e monitorada"}
            ]
            for it in itens_iniciais:
                item = ItemServicoModel(
                    uuid_publico=str(uuid.uuid4()),
                    codigo=it["codigo"],
                    nome=it["nome"],
                    categoria=it["categoria"],
                    preco_unitario=it["preco_unitario"],
                    descricao=it["descricao"],
                    is_ativo=1
                )
                db.add(item)
            db.commit()

        # 4. Hóspedes Iniciais (RF-001/002)
        hospedes_iniciais = [
            {"nome": "Carlos Eduardo Mendes", "email": "carlos.mendes@email.com", "cpf": "52998224725", "telefone": "11987654321", "data_nascimento": "1985-04-12", "observacoes": "Hóspede corporativo VIP"},
            {"nome": "Fernanda Beatriz de Souza", "email": "fernanda.souza@email.com", "cpf": "83184523000", "telefone": "21998877665", "data_nascimento": "1992-08-23", "observacoes": "Preferência por andar alto"},
            {"nome": "Roberto Lima Albuquerque", "email": "roberto.lima@email.com", "cpf": "01234567890", "telefone": "31976543210", "data_nascimento": "1978-11-30", "observacoes": "Check-in tardio"}
        ]
        for h in hospedes_iniciais:
            h_db = db.query(HospedeModel).filter_by(cpf=h["cpf"]).first()
            if not h_db:
                dt_nasc = datetime.strptime(h["data_nascimento"], "%Y-%m-%d").date()
                hosp = HospedeModel(
                    uuid_publico=str(uuid.uuid4()),
                    nome=h["nome"],
                    email=h["email"],
                    cpf=h["cpf"],
                    telefone=h["telefone"],
                    data_nascimento=dt_nasc,
                    observacoes=h["observacoes"],
                    is_ativo=1
                )
                db.add(hosp)
        db.commit()

        # 5. Hospedagens Ativas e Consumos de Frigobar (RF-004 e RF-005)
        if db.query(HospedagemModel).filter_by(status="ATIVA").count() == 0:
            hosp_carlos = db.query(HospedeModel).filter_by(email="carlos.mendes@email.com").first()
            quarto_105 = db.query(AcomodacaoModel).filter_by(numero="105").first()
            
            # Se não tiver o 105, pega o primeiro quarto disponível para colocar Carlos
            if not quarto_105:
                quarto_105 = db.query(AcomodacaoModel).filter_by(numero="101").first()

            if hosp_carlos and quarto_105:
                quarto_105.status = "OCUPADO"
                estadia_carlos = HospedagemModel(
                    uuid_publico=str(uuid.uuid4()),
                    id_acomodacao=quarto_105.id,
                    id_hospede=hosp_carlos.id,
                    data_checkin=datetime.utcnow() - timedelta(days=1),
                    data_prevista_checkout=datetime.utcnow() + timedelta(days=2),
                    tarifa_diaria_aplicada=quarto_105.tarifa_base,
                    status="ATIVA",
                    observacoes="Check-in efetuado via auto-seed demonstrativo."
                )
                db.add(estadia_carlos)
                db.commit()
                db.refresh(estadia_carlos)

                # Lança 2 itens de frigobar na estadia do Carlos
                item_agua = db.query(ItemServicoModel).filter_by(codigo="FRIG-001").first()
                item_ipa = db.query(ItemServicoModel).filter_by(codigo="FRIG-004").first()
                if item_agua:
                    c1 = ConsumoModel(
                        uuid_publico=str(uuid.uuid4()),
                        id_hospedagem=estadia_carlos.id,
                        id_item_servico=item_agua.id,
                        quantidade=2,
                        valor_unitario=item_agua.preco_unitario,
                        valor_total=item_agua.preco_unitario * 2,
                        status="CONFIRMADO",
                        data_lancamento=datetime.utcnow() - timedelta(hours=6)
                    )
                    db.add(c1)
                if item_ipa:
                    c2 = ConsumoModel(
                        uuid_publico=str(uuid.uuid4()),
                        id_hospedagem=estadia_carlos.id,
                        id_item_servico=item_ipa.id,
                        quantidade=1,
                        valor_unitario=item_ipa.preco_unitario,
                        valor_total=item_ipa.preco_unitario,
                        status="CONFIRMADO",
                        data_lancamento=datetime.utcnow() - timedelta(hours=3)
                    )
                    db.add(c2)
                db.commit()

        logger.info("Auto-seeding completo de todas as entidades concluído com sucesso.")

    except Exception as e:
        logger.warning(f"Aviso ao verificar dados iniciais: {e}")
        db.rollback()
    finally:
        db.close()
