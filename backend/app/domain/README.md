# Domain layer (Layer 1)

Pure business entities, value objects, and domain exceptions.

**Strangler Fig:** runtime models remain in `app.modules.*_model` until each
bounded context is migrated. Do not import FastAPI / SQLAlchemy here.
