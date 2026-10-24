from datetime import date

from eu_impact.classify import citations_excluding_self, citations_in_window, combined_output_type, is_top10, timing


def test_timing_day_and_year():
    start = date(2018, 6, 1)
    end = date(2020, 6, 1)
    assert timing(date(2018, 1, 1), start, end) == "before"
    assert timing(date(2019, 1, 1), start, end) == "during"
    assert timing(date(2021, 1, 1), start, end) == "after"
    assert timing(date(2018, 1, 1), start, end, precision="year") == "during"
    assert timing(date(2021, 1, 1), start, end, precision="year") == "after"
    assert timing(None, start, end) is None


def test_citations_in_window_sums_years_up_to_the_horizon():
    counts = [
        {"year": 2020, "cited_by_count": 5},
        {"year": 2021, "cited_by_count": 7},
        {"year": 2024, "cited_by_count": 9},
    ]
    assert citations_in_window(counts, date(2020, 12, 31), 3) == 12
    assert citations_in_window([], date(2020, 1, 1), 3) is None
    assert citations_in_window(counts, None, 3) is None


def test_citations_excluding_self_treats_an_empty_list_as_zero():
    counts = [{"year": 2020, "cited_by_count": 4}, {"year": 2024, "cited_by_count": 9}]
    assert citations_excluding_self(counts, date(2020, 12, 31), 3) == 4
    assert citations_excluding_self([], date(2020, 1, 1), 3) == 0
    assert citations_excluding_self(None, date(2020, 1, 1), 3) is None
    assert citations_excluding_self(counts, None, 3) is None


def test_top10_uses_the_flag_then_the_percentile():
    assert is_top10(True, 0.2) is True
    assert is_top10(None, 0.9) is True
    assert is_top10(None, 0.89) is False
    assert is_top10(None, None) is None


def test_output_type_flags_reviews_without_matching_reviewed():
    assert combined_output_type(["Peer reviewed articles"]) == "article"
    assert combined_output_type(["Review"]) == "review"
    assert combined_output_type([], openalex_type="review") == "review"
    assert combined_output_type(["dataset"]) == "dataset"
    assert combined_output_type(["software"]) == "software"
