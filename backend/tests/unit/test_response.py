"""Tests for the ApiResponse envelope."""

from app.application.common.pagination import PageRequest, PageResult
from app.presentation.common.response import ApiResponse, paginated_response


class TestApiResponse:
    def test_wraps_data_with_no_meta_by_default(self) -> None:
        response = ApiResponse[int](data=42)

        assert response.data == 42
        assert response.meta is None


class TestPaginatedResponse:
    def test_wraps_items_with_pagination_meta(self) -> None:
        page_result = PageResult.create(
            ["a", "b"], total=5, request=PageRequest(page=1, page_size=2)
        )

        response = paginated_response(page_result)

        assert response.data == ["a", "b"]
        assert response.meta == {
            "pagination": {"page": 1, "page_size": 2, "total": 5, "total_pages": 3}
        }
