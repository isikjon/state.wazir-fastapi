from app.api.v1.endpoints import users, auth, properties, requests, support
 
api_router.include_router(support.router, prefix="/support", tags=["support"]) 