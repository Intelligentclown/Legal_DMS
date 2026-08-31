"""SQLAlchemy persistence models for the complete Stage 2 database schema.

These are persistence-layer ORM models, not domain entities — see
ADR-0008 for why. Models define columns and FK constraints only; ORM
`relationship()` navigation is deliberately NOT declared here — it's a
query-ergonomics convenience best added by the first feature that needs a
specific traversal (with the right cascade/loading behavior for that use
case), not guessed at during schema design with no consuming code to
validate against.

Every module here must be imported somewhere reachable from
`alembic/env.py` (directly or transitively) so `Base.metadata` — and
therefore `alembic revision --autogenerate` — sees every table.
"""

from app.infrastructure.persistence.models import activity as activity
from app.infrastructure.persistence.models import client as client
from app.infrastructure.persistence.models import document as document
from app.infrastructure.persistence.models import financial as financial
from app.infrastructure.persistence.models import geography as geography
from app.infrastructure.persistence.models import identity as identity
from app.infrastructure.persistence.models import matter as matter
from app.infrastructure.persistence.models import organization as organization
from app.infrastructure.persistence.models import property as property
from app.infrastructure.persistence.models import scheduling as scheduling
from app.infrastructure.persistence.models import storage as storage
from app.infrastructure.persistence.models import system as system
from app.infrastructure.persistence.models import workflow as workflow
