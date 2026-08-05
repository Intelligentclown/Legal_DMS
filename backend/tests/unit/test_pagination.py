"""Tests for the pagination framework."""

import pytest

from app.application.common.pagination import MAX_PAGE_SIZE, PageRequest, PageResult


class TestPageRequest:
    def test_defaults(self) -> None:
        request = PageRequest()

        assert request.page == 1
        assert request.limit == request.page_size

    def test_offset_is_zero_on_first_page(self) -> None:
        assert PageRequest(page=1, page_size=20).offset == 0

    def test_offset_advances_by_page_size(self) -> None:
        assert PageRequest(page=3, page_size=20).offset == 40

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValueError, match="page must be >= 1"):
            PageRequest(page=0)

    def test_rejects_page_size_above_max(self) -> None:
        with pytest.raises(ValueError, match="page_size must be between"):
            PageRequest(page_size=MAX_PAGE_SIZE + 1)


class TestPageResult:
    def test_create_computes_total_pages(self) -> None:
        result = PageResult.create([1, 2, 3], total=25, request=PageRequest(page=1, page_size=10))

        assert result.total_pages == 3
        assert result.items == [1, 2, 3]

    def test_total_pages_is_zero_when_page_size_is_zero(self) -> None:
        result = PageResult(items=[], total=0, page=1, page_size=0)

        assert result.total_pages == 0
