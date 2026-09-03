# Grand Plaza Hotel Management System
## Laboratório de Inovação III — Prof. Edilberto Silva — 2026
### Entrega: GRUPO-06 — SEMANA-01 (RF-001: Cadastro Seguro de Hóspedes)

---

## 👥 1. Identificação da Equipe

| ID | Nome Completo | Papel Primário | Papel Secundário | E-mail Institucional / Contato |
| :---: | :--- | :--- | :--- | :--- |
| 1 | **João Miguel Paiva Velloso Ramos Pereira** | Scrum Master | Desenvolvedor Back-End | `jguel0713@gmail.com` |
| 2 | **João Victor Sousa da Conceição** | Desenvolvedor Front-End | QA / SecDevOps | `joao47064706@edu.df.senac.br` |

**Lista de Integrantes para o Moodle:**  
`jguel0713@gmail.com; joao47064706@edu.df.senac.br`

---

## 🌐 2. Links de Demonstração e Produção (Túnel Cloudflare HTTPS)

- **Aplicação Web (Frontend + Backend):** [https://rfc-display-tests-min.trycloudflare.com](https://rfc-display-tests-min.trycloudflare.com)
- **Documentação Interativa Swagger / OpenAPI:** [https://rfc-display-tests-min.trycloudflare.com/docs](https://rfc-display-tests-min.trycloudflare.com/docs)
- **Healthcheck da API:** [https://rfc-display-tests-min.trycloudflare.com/api/v1/health](https://rfc-display-tests-min.trycloudflare.com/api/v1/health)
- **Contrato Estático OpenAPI:** [`docs/api/swagger.json`](docs/api/swagger.json)

---

## 📁 3. Estrutura Canônica do Projeto

```text
Trabalho_Edilberto/
├── docs/
│   ├── requisitos/
│   │   └── RF-001-cadastro-hospede.md        <-- DOCUMENTO DE ESPECIFICAÇÃO OFICIAL (7 TÓPICOS - 100%)
│   └── api/
│       └── swagger.json                       <-- Contrato OpenAPI 3.1 gerado pelo FastAPI
├── src/
│   └── rf-001-cadastro-hospede/
│       ├── index.html                        <-- Interface HTML5 com Design Antisslop (CSS embutido)
│       ├── app.js                            <-- Manipulador de Estados, Validação Módulo 11 e Fetch
│       ├── main.py                           <-- API REST FastAPI com Rate Limiting e Security Headers
│       ├── schemas.py                        <-- Validação Pydantic v2 (Módulo 11 para CPF e RFC 5322)
│       ├── models.py                         <-- Modelos ORM SQLAlchemy alinhados ao DDL
│       ├── database.py                       <-- Provedor resiliente de Banco (SQLite / MySQL)
│       ├── hotel_grand_plaza.db              <-- Banco SQLite local com persistência ativa
│       ├── requirements.txt                  <-- Dependências Python
│       └── README.md                         <-- Guia local de execução do RF-001
├── database/
│   ├── ddl/
│   │   └── rf-001-hospedes-ddl.sql           <-- Script DDL com chaves primárias, uniques e índices
│   └── seeds/
│       └── hospedes-seeds.sql                <-- Carga de dados de teste (Seeds)
├── Contexto/                                 <-- Regras normativas da disciplina
│   ├── Formatação Projeto e .md.md
│   ├── documentation-rules.md
│   ├── backend-rules.md
│   ├── frontend-rules.md
│   └── db-rules.md
└── README.md                                 <-- Este arquivo geral do repositório
```

---

## 🚀 4. Como Executar a Aplicação Localmente

### Opção A: No WSL (Ubuntu) com Túnel Cloudflare (Configuração Oficial)
1. Abra o terminal do WSL:
   ```bash
   cd /mnt/c/Users/Dimi/Desktop/Trabalho_Edilberto/src/rf-001-cadastro-hospede
   source .venv/bin/activate
   ```
2. Inicie o servidor ASGI FastAPI:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
3. Em outro terminal, exponha o túnel HTTPS Cloudflare:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

### Opção B: No Windows Direto (PowerShell)
1. Navegue até a pasta do requisito:
   ```powershell
   cd src\rf-001-cadastro-hospede
   ```
2. Instale as dependências:
   ```powershell
   pip install -r requirements.txt
   ```
3. Execute o servidor:
   ```powershell
   python main.py
   ```
4. Acesse no navegador: `http://localhost:8000`

---

## 🔒 5. Segurança OWASP e Integridade de Dados
- **OWASP A03 (SQL Injection):** Neutralizado através do uso estrito de Prepared Statements e ORM SQLAlchemy, sem interpolação de strings em queries.
- **Validação Algorítmica:** Algoritmo oficial Módulo 11 executado de forma dual (frontend no `app.js` e backend no `schemas.py`).
- **Trilha de Auditoria (LGPD):** Todo cadastro gera registro automático de IP de origem e timestamp na tabela `tb_audit_logs`.
- **Headers HTTP de Proteção:** Injeção de `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` e Rate Limiting de 30 req/min por IP.

---

## 📦 6. Instruções para Gerar o Pacote de Entrega (.zip)
Conforme a regra do edital (`GRUPO-[99]-SEMANA-[99].zip`):
1. O arquivo deve se chamar: **`GRUPO-06-SEMANA-01.zip`**.
2. Remover pastas temporárias pesadas (`.venv`, `__pycache__`) antes de compactar.
3. Compactar todo o conteúdo da pasta do projeto.
