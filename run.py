import os
import sys
from pathlib import Path
import uvicorn

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  🏨 GRAND PLAZA HOTEL — SERVIÇO WEB DEMO (RF-001 a RF-005)")
    print("  🌐 Interface Web (SPA): http://localhost:8000")
    print("  📑 Documentação Interativa (Swagger): http://localhost:8000/docs")
    print("  🔑 Credencial Padrão Seeded: admin@hotelgrandplaza.com.br / Admin@2026")
    print("="*70 + "\n")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

