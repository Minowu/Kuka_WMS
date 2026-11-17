# Infrastructure layer (Layer 4)

SQLAlchemy models/repositories, external clients (KUKA Fleet, Redis), security,
queue implementations.

**Strangler Fig:** current persistence and clients remain under `app.modules`
and `app.core` until moved behind ports.
