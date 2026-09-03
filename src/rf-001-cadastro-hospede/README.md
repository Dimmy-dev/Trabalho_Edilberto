# Como Executar o Backend — RF-001 (Cadastro de Hóspede)

Este módulo implementa a API REST para o Requisito Funcional 001, utilizando **Python 3.11+, FastAPI e SQLAlchemy**.

---

## 🚀 Como Executar Localmente ou no WSL

### 1. Criar e Ativar Ambiente Virtual
```bash
python -m venv venv

# No Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# No Linux / WSL:
source venv/bin/activate
```

### 2. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 3. Executar o Servidor FastAPI
```bash
python main.py
```
O servidor iniciará em `http://127.0.0.1:8000`.

### 4. Acessar a Documentação Interativa Swagger / OpenAPI
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON:** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

### 5. Exportar Contrato Swagger Obrigatório (Tópico 7)
Com o servidor rodando, acesse no navegador ou via curl:
```bash
curl http://127.0.0.1:8000/export-swagger-json
```
Isso salvará automaticamente o arquivo `docs/api/swagger.json` exigido na entrega.
