"""Point d'entrée principal pour l'application StockVision."""
import os
from app import create_app

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    print("==================================================")
    print("  StockVision — Suivi et Analyse des Stocks")
    print("  Application Flask démarrée sur : http://127.0.0.1:5000")
    print("==================================================")
    app.run(host="127.0.0.1", port=5000, debug=True)
