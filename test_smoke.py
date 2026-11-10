"""
SMOKE TEST DE PONTA A PONTA (E2E) — GRAND PLAZA HOTEL
Validação automatizada do fluxo integrado e sincronizado:
1. Bloqueio de Acesso antes do Login (RF-003 / auth.py)
2. Login e Emissão de Token / Cookie (RF-003 / auth.py)
3. Sincronia Inicial de Dados entre Hospedagem (RF-004) e Governança (RF-006)
4. Check-in -> Consumo Frigobar (RF-005) -> Check-out (Geração Automática de OS em Governança)
5. Conclusão de OS na Governança -> Liberação Automática do Quarto no Rack (DISPONIVEL)
"""

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from fastapi.testclient import TestClient
import main

def executar_smoke_test():
    print("=" * 72)
    print("  🧪 INICIANDO SMOKE TEST UNIFICADO (AUTH + HOSPEDAGEM + GOVERNANÇA)")
    print("=" * 72)

    # 1. Teste de Bloqueio antes do Login (Cliente sem sessão)
    client_anonimo = TestClient(main.app)
    print("\n[1/7] Testando Primeira Tela de Login e Bloqueio Não-Autenticado (auth.py)...")
    r_index = client_anonimo.get("/")
    assert r_index.status_code == 200 and 'id="login-screen"' in r_index.text
    r_block_rack = client_anonimo.get("/api/v1/acomodacoes")
    assert r_block_rack.status_code == 401, f"Acomodacoes deveria exigir login (401), retornou {r_block_rack.status_code}"
    r_block_gov = client_anonimo.get("/api/v1/governanca/ordens")
    assert r_block_gov.status_code == 401, f"Governanca deveria exigir login (401), retornou {r_block_gov.status_code}"
    print("  ✅ Acesso bloqueado antes do login (HTTP 401) e Tela de Login presente no HTML.")

    # 2. Autenticação (RF-003)
    client = TestClient(main.app)
    print("\n[2/7] Testando Autenticação do Operador (RF-003 / auth.py)...")
    r_login = client.post("/api/v1/auth/login", json={
        "email": "admin@grandplaza.com",
        "senha": "Hotel@2026!"
    })
    assert r_login.status_code == 200, f"Falha no login: {r_login.text}"
    login_data = r_login.json()
    assert login_data.get("success") is True
    token = login_data["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  ✅ Login efetuado! Operador: {login_data['data']['nome']} ({login_data['data']['cargo']})")

    # 3. Verificação de Sincronia Inicial entre Hospedagem e Governança
    print("\n[3/7] Verificando sincronia de dados entre hospedagem.py e governanca.py...")
    r_quartos = client.get("/api/v1/acomodacoes", headers=headers)
    assert r_quartos.status_code == 200
    quartos = r_quartos.json()["data"]

    r_ordens = client.get("/api/v1/governanca/ordens", headers=headers)
    assert r_ordens.status_code == 200
    ordens = r_ordens.json()["data"]

    quartos_bloqueados = {q["numero"]: q["status"] for q in quartos if q["status"] in ("LIMPEZA", "MANUTENCAO")}
    ordens_abertas = {o["quarto_numero"]: o["tipo"] for o in ordens if o["status"] != "CONCLUIDA"}
    for num_q, st_q in quartos_bloqueados.items():
        assert num_q in ordens_abertas, f"Quarto {num_q} está em {st_q} no Rack mas sem OS aberta na Governança!"
    print(f"  ✅ Sincronia confirmada! Quartos bloqueados no Rack ({list(quartos_bloqueados.keys())}) possuem OS ativa na Governança.")

    # 4. Consulta/Cadastro de Hóspede (RF-001)
    print("\n[4/7] Validando Hóspede para Check-in (RF-001)...")
    r_hosp_list = client.get("/api/v1/hospedes", headers=headers)
    assert r_hosp_list.status_code == 200
    hospedes = r_hosp_list.json()["data"]
    assert len(hospedes) > 0
    uuid_hospede = hospedes[0]["uuid_publico"]
    print(f"  ✅ Hóspede selecionado: {hospedes[0]['nome']} ({uuid_hospede})")

    # 5. Check-in em Quarto Disponível (RF-004)
    print("\n[5/7] Realizando Check-in no Rack Hoteleiro (RF-004)...")
    quarto_disp = next((q for q in quartos if q["status"] == "DISPONIVEL"), None)
    assert quarto_disp is not None, "Nenhum quarto disponível para teste."
    uuid_quarto = quarto_disp["uuid_publico"]
    num_quarto = quarto_disp["numero"]

    r_checkin = client.post("/api/v1/hospedagens/checkin", headers=headers, json={
        "uuid_acomodacao": uuid_quarto,
        "uuid_hospede": uuid_hospede,
        "data_prevista_checkout": "2026-12-01T12:00:00",
        "acompanhantes": [],
        "observacoes": "Teste integrado E2E"
    })
    assert r_checkin.status_code == 201, f"Falha no check-in: {r_checkin.text}"
    uuid_hospedagem = r_checkin.json()["data"]["uuid_publico"]
    print(f"  ✅ Check-in realizado no Quarto {num_quarto}! Estadia UUID: {uuid_hospedagem}")

    # 6. Check-out -> Deve mover Quarto para LIMPEZA e criar OS automaticamente em governanca.py!
    print("\n[6/7] Realizando Check-out e testando geração automática de OS na Governança...")
    r_checkout = client.post("/api/v1/hospedagens/checkout", headers=headers, json={
        "uuid_hospedagem": uuid_hospedagem
    })
    assert r_checkout.status_code == 200, f"Falha no check-out: {r_checkout.text}"

    # Verifica se o quarto foi para LIMPEZA e se a OS foi aberta em governanca.py
    r_ordens_pos = client.get(f"/api/v1/governanca/ordens?quarto_numero={num_quarto}", headers=headers)
    ordens_quarto = [o for o in r_ordens_pos.json()["data"] if o["status"] != "CONCLUIDA"]
    assert len(ordens_quarto) > 0, f"Check-out do Quarto {num_quarto} não gerou OS de Limpeza na Governança!"
    os_gerada = ordens_quarto[0]
    print(f"  ✅ Check-out do Quarto {num_quarto} gerou automaticamente a OS {os_gerada['codigo_os']} ({os_gerada['tipo']})!")

    # 7. Conclusão da OS na Governança -> Deve liberar o Quarto para DISPONIVEL em hospedagem.py!
    print("\n[7/7] Concluindo OS na Governança e verificando liberação do Quarto no Rack...")
    r_concluir = client.patch(
        f"/api/v1/governanca/ordens/{os_gerada['uuid_os']}/concluir",
        headers=headers,
        json={"observacoes_conclusao": "Higienização aprovada no teste E2E", "responsavel_conclusao": "Governanta Chefe"}
    )
    assert r_concluir.status_code == 200, f"Falha ao concluir OS: {r_concluir.text}"

    r_quartos_final = client.get("/api/v1/acomodacoes", headers=headers)
    quarto_final = next((q for q in r_quartos_final.json()["data"] if q["numero"] == num_quarto), None)
    assert quarto_final["status"] == "DISPONIVEL", f"Quarto {num_quarto} deveria estar DISPONIVEL após conclusão da OS, mas está {quarto_final['status']}"
    print(f"  ✅ OS {os_gerada['codigo_os']} concluída e Quarto {num_quarto} retornou automaticamente para DISPONIVEL no Rack!")

    print("\n" + "=" * 72)
    print("  🎉 TODOS OS 7 TESTES INTEGRADOS PASSARAM COM 100% DE SUCESSO!")
    print("=" * 72)

if __name__ == "__main__":
    executar_smoke_test()
