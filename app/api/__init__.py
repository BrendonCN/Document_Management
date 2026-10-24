from fastapi import APIRouter

from app.api import audit, auth, content, nodes, users, versions

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(nodes.router)
api_router.include_router(versions.router)
api_router.include_router(content.router)
api_router.include_router(audit.router)
