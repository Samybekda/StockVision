import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configuration de base de StockVision."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "stockvision-secret-key-miage-2026")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'stockvision.db')}"
    )


class DevelopmentConfig(Config):
    """Configuration pour le développement local."""
    DEBUG = True


class TestingConfig(Config):
    """Configuration isolée pour les tests unitaires et d'intégration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_SESSION_OPTIONS = {"expire_on_commit": False}


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
