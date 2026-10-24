from eu_impact.pull.citations import counts_from_groups, nonself_filter, shares_name


def test_group_counts_keep_numeric_years():
    groups = [
        {"key": "2021", "count": 3},
        {"key": "unknown", "count": 1},
        {"key": 2022, "count": 4},
    ]
    assert counts_from_groups(groups) == [
        {"year": 2021, "cited_by_count": 3},
        {"year": 2022, "cited_by_count": 4},
    ]


def test_name_match_ignores_order_and_punctuation():
    assert shares_name(["Lohse, Detlef"], ["Detlef Lohse"])
    assert shares_name(["Giulio Iovine"], ["Xiaojue Zhu"]) is False
    assert shares_name([], ["Detlef Lohse"]) is False


def test_nonself_filter_excludes_every_author():
    assert nonself_filter("https://openalex.org/W123", ["A1", "A2"]) == (
        "cites:W123,authorships.author.id:!A1,authorships.author.id:!A2"
    )
