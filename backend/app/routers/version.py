from fastapi import APIRouter

router = APIRouter(tags=["System"])


@router.get("/version")
def get_version():
    """Gibt die aktuelle App-Version zurück."""
    from ..main import APP_VERSION
    return {
        "version": APP_VERSION,
        "app": "BIW Pokal",
        "status": "beta" if "beta" in APP_VERSION else "stable"
    }
