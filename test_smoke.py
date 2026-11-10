"""
SMOKE TEST DE PONTA A PONTA (E2E) — GRAND PLAZA HOTEL
Validação automatizada do fluxo integrado:
RF-003 (Auth) -> RF-001/002 (Hóspedes) -> RF-004 (Check-in/Rack) -> RF-005 (Consumos) -> RF-004 (Check-out)
"""

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

def executar_smoke_test():
    print("=" * 70)
    print("  🧪 INICIANDO SMOKE TEST DE CICLO COMPLETO DO HOTEL")
    print("=" * 70)

    # 1. Teste de Frontend e Documentação
    print("\n[1/6] Testando rotas base da aplicação...")
    r_index = client.get("/")
    assert r_index.status_code == 200, f"Falha ao carregar SPA: {r_index.status_code}"
    r_docs = client.get("/docs")
    assert r_docs.status_code == 200, f"Falha ao carregar Swagger: {r_docs.status_code}"
    print("  ✅ Frontend SPA e Swagger Docs ativos (HTTP 200).")

    # 2. Autenticação (RF-003)
    print("\n[2/6] Testando Autenticação do Administrador (RF-003)...")
    login_payload = {
        "email": "admin@hotelgrandplaza.com.br",
        "senha": "Admin@2026"
    }
    r_login = client.post("/api/v1/auth/login", json=login_payload)
    assert r_login.status_code == 200, f"Falha no login: {r_login.text}"
    login_data = r_login.json()
    assert login_data.get("success") is True
    token = login_data["data"]["token"]
    print(f"  ✅ Login efetuado com sucesso! Usuário: {login_data['data']['operador']['nome']}")

    # 3. Cadastro de Hóspede (RF-001 / RF-002)
    print("\n[3/6] Testando Cadastro e Atualização de Hóspede (RF-001 e RF-002)...")
    # Gerador de CPF válido para teste
    hospede_payload = {
        "nome": "Carlos Drummond de Andrade",
        "email": "drummond@poesia.com.br",
        "cpf": "12345678909",
        "telefone": "11987654321",
        "endereco": "Rua dos Poetas, 100",
        "cidade": "Itabira",
        "estado": "MG",
        "pais": "Brasil"
    }
    r_hospede = client.post("/api/v1/hospedes", json=hospede_payload)
    if r_hospede.status_code == 409:
        print("  ℹ️ Hóspede de teste já cadastrado, consultando...")
        r_list = client.get("/api/v1/hospedes?termo=12345678909")
        hospedes = r_list.json().get("data", [])
        uuid_hospede = hospedes[0]["uuid_hospede"]
    else:
        assert r_hospede.status_code == 201, f"Falha ao cadastrar hóspede: {r_hospede.text}"
        uuid_hospede = r_hospede.json()["data"]["uuid_hospede"]
    print(f"  ✅ Hóspede pronto para estadia. UUID: {uuid_hospede}")

    # 4. Rack de Quartos e Check-in (RF-004)
    print("\n[4/6] Testando Rack de Quartos e Check-in Atômico (RF-004)...")
    r_quartos = client.get("/api/v1/acomodacoes")
    assert r_quartos.status_code == 200
    quartos = r_quartos.json().get("data", [])
    assert len(quartos) > 0, "Nenhum quarto encontrado no rack."
    
    # Encontra o primeiro quarto DISPONIVEL
    quarto_disponivel = next((q for q in quartos if q["status"] == "DISPONIVEL"), None)
    if not quarto_disponivel:
        # Se nenhum disponível, libera um em limpeza
        quarto_limpeza = next((q for q in quartos if q["status"] in ["LIMPEZA", "MANUTENCAO"]), quartos[0])
        client.patch(f"/api/v1/acomodacoes/{quarto_limpeza['uuid_quarto']}/status", json={"novo_status": "DISPONIVEL"})
        quarto_disponivel = quarto_limpeza

    uuid_quarto = quarto_disponivel["uuid_quarto"]
    num_quarto = quarto_disponivel["numero"]
    print(f"  ℹ️ Selecionado Quarto {num_quarto} para Check-in.")

    checkin_payload = {
        "uuid_hospede": uuid_hospede,
        "uuid_quarto": uuid_quarto,
        "previsao_saida": "2026-11-20T12:00:00",
        "observacoes": "Check-in do teste de fumaça E2E"
    }
    r_checkin = client.post("/api/v1/hospedagens/checkin", json=checkin_payload)
    assert r_checkin.status_code == 201, f"Falha no check-in: {r_checkin.text}"
    hospedagem_data = r_checkin.json()["data"]
    uuid_hospedagem = hospedagem_data["uuid_hospedagem"]
    print(f"  ✅ Check-in concluído com sucesso! Estadia UUID: {uuid_hospedagem}")

    # 5. Frigobar e Consumo (RF-005)
    print("\n[5/6] Testando Catálogo de Frigobar e Lançamento de Consumo (RF-005)...")
    r_cat = client.get("/api/v1/itens-servicos")
    assert r_cat.status_code == 200
    itens = r_cat.json().get("data", [])
    assert len(itens) > 0, "Catálogo de frigobar vazio."
    item_teste = itens[0]
    print(f"  ℹ️ Lançando item: {item_teste['nome']} (R$ {item_teste['preco_unitario']})")

    consumo_payload = {
        "uuid_hospedagem": uuid_hospedagem,
        "uuid_item": item_teste["uuid_item"],
        "quantidade": 2,
        "observacoes": "Consumo de teste"
    }
    r_consumo = client.post("/api/v1/consumos", json=consumo_payload)
    assert r_consumo.status_code == 201, f"Falha no lançamento de consumo: {r_consumo.text}"
    
    # Conferência do Extrato
    r_extrato = client.get(f"/api/v1/consumos/extrato/{uuid_hospedagem}")
    assert r_extrato.status_code == 200
    extrato_data = r_extrato.json()["data"]
    print(f"  ✅ Consumo registrado. Total consumido no quarto: R$ {extrato_data.get('valor_total_consumo', 0):.2f}")

    # 6. Check-out e Faturamento (RF-004)
    print("\n[6/6] Testando Check-out e Fechamento de Conta (RF-004)...")
    checkout_payload = {
        "uuid_hospedagem": uuid_hospedagem,
        "forma_pagamento": "CARTAO_CREDITO",
        "observacoes": "Check-out do teste de fumaça E2E"
    }
    r_checkout = client.post("/api/v1/hospedagens/checkout", json=checkout_payload)
    assert r_checkout.status_code == 200, f"Falha no check-out: {r_checkout.text}"
    checkout_data = r_checkout.json()["data"]
    total_geral = checkout_data.get("valor_total", 0)
    print(f"  ✅ Check-out concluído! Faturamento total: R$ {total_geral:.2f}")

    # Validação do estado final do quarto (deve estar em LIMPEZA)
    r_quartos_pos = client.get("/api/v1/acomodacoes")
    quarto_pos = next((q for q in r_quartos_pos.json()["data"] if q["uuid_quarto"] == uuid_quarto), None)
    assert quarto_pos["status"] == "LIMPEZA", f"Quarto deveria estar em LIMPEZA, mas está: {quarto_pos['status']}"
    print(f"  ✅ Máquina de estados validada: Quarto {num_quarto} transacionou para status LIMPEZA.")

    print("\n" + "=" * 70)
    print("  🎉 TODOS OS TESTES PASSARAM COM 100% DE SUCESSO!")
    print("  🏆 O SERVIÇO WEB HOTEL_SERVICE ESTÁ PRONTO E HOMOLOGADO.")
    print("=" * 70)

if __name__ == "__main__":
    executar_smoke_test()

