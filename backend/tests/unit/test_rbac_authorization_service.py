"""Tests for T53's `RbacAuthorizationService` (checks `require_permission()`
against the caller's roles via a pre-loaded role -> permission-codes
mapping -- see the class's own docstring for why that snapshot is
pre-loaded rather than queried per call).
"""

from __future__ import annotations

import pytest

from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.auth import CurrentUser
from app.infrastructure.auth.rbac_authorization_service import RbacAuthorizationService


def _service(mapping: dict[str, frozenset[str]] | None = None) -> RbacAuthorizationService:
    return RbacAuthorizationService(mapping or {})


class TestAnonymousCallers:
    def test_anonymous_caller_is_denied_regardless_of_mapping(self) -> None:
        service = _service({"Advocate": frozenset({"matters:read"})})

        with pytest.raises(ForbiddenError):
            service.require_permission(CurrentUser(), "matters:read")

    def test_anonymous_caller_with_roles_but_not_authenticated_is_still_denied(self) -> None:
        # is_authenticated is the deciding flag, not whether `roles` happens to be non-empty.
        service = _service({"Advocate": frozenset({"matters:read"})})
        user = CurrentUser(roles=frozenset({"Advocate"}), is_authenticated=False)

        with pytest.raises(ForbiddenError):
            service.require_permission(user, "matters:read")


class TestAuthenticatedCallers:
    def test_authenticated_user_with_granting_role_is_permitted(self) -> None:
        service = _service({"Advocate": frozenset({"matters:read"})})
        user = CurrentUser(roles=frozenset({"Advocate"}), is_authenticated=True)

        service.require_permission(user, "matters:read")  # does not raise

    def test_authenticated_user_without_granting_role_is_denied(self) -> None:
        service = _service({"Advocate": frozenset({"matters:read"})})
        user = CurrentUser(roles=frozenset({"Clerk"}), is_authenticated=True)

        with pytest.raises(ForbiddenError):
            service.require_permission(user, "matters:read")

    def test_authenticated_user_with_no_roles_is_denied(self) -> None:
        service = _service({"Advocate": frozenset({"matters:read"})})
        user = CurrentUser(roles=frozenset(), is_authenticated=True)

        with pytest.raises(ForbiddenError):
            service.require_permission(user, "matters:read")

    def test_permission_granted_by_one_of_several_roles_is_permitted(self) -> None:
        service = _service(
            {
                "Clerk": frozenset({"matters:read"}),
                "Accountant": frozenset({"financial:read"}),
            }
        )
        user = CurrentUser(roles=frozenset({"Clerk", "Accountant"}), is_authenticated=True)

        service.require_permission(user, "financial:read")  # does not raise

    def test_role_absent_from_mapping_does_not_raise_a_lookup_error(self) -> None:
        # A role the caller has that simply isn't in role_permissions yet (e.g. unseeded,
        # T66) must fail the permission check cleanly, not KeyError.
        service = _service({})
        user = CurrentUser(roles=frozenset({"Read Only"}), is_authenticated=True)

        with pytest.raises(ForbiddenError):
            service.require_permission(user, "matters:read")

    def test_permission_code_must_match_exactly(self) -> None:
        service = _service({"Advocate": frozenset({"matters:read"})})
        user = CurrentUser(roles=frozenset({"Advocate"}), is_authenticated=True)

        with pytest.raises(ForbiddenError):
            service.require_permission(user, "matters:write")
