# Adapters layer (Layer 3)

HTTP controllers, Pydantic schemas, websocket, Celery task adapters.

**Strangler Fig:** active routers remain in `app.modules.*_api`. New thin
controllers will land under `adapters/api/v1/` as modules are migrated.
