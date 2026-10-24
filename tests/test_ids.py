from eu_impact.ids import extract_dois, normalize_doi, normalize_grant_id


def test_grant_id_from_plain_number():
    assert normalize_grant_id("696656") == "696656"


def test_grant_id_strips_ga_prefix_and_spaces():
    assert normalize_grant_id(" GA 696656 ") == "696656"


def test_grant_id_from_cordis_url():
    assert normalize_grant_id("https://cordis.europa.eu/project/id/642332") == "642332"


def test_grant_id_from_grant_doi():
    assert normalize_grant_id("10.3030/675440") == "675440"


def test_grant_id_from_zenodo_funder_form():
    assert normalize_grant_id("10.13039/501100000780::675440") == "675440"


def test_grant_id_rejects_blank():
    assert normalize_grant_id(None) is None
    assert normalize_grant_id("  ") is None
    assert normalize_grant_id("not-a-grant") is None


def test_doi_strips_resolver_and_lowercases():
    assert normalize_doi("https://doi.org/10.1002/adfm.201703976") == "10.1002/adfm.201703976"
    assert normalize_doi("https://dx.doi.org/urn:doi:10.1021/acsami.7b08811") == "10.1021/acsami.7b08811"


def test_doi_rejects_funder_and_grant_ids():
    assert normalize_doi("10.13039/501100000780") is None
    assert normalize_doi("10.13039/501100000780696656") is None
    assert normalize_doi("10.3030/696656") is None


def test_doi_keeps_zenodo_doi():
    assert normalize_doi("10.5281/zenodo.3690070") == "10.5281/zenodo.3690070"


def test_extract_dois_skips_funder_ids_in_the_same_string():
    text = "10.13039/501100000780696656 https://dx.doi.org/urn:doi:10.1002/adfm.201703976"
    assert extract_dois(text) == ["10.1002/adfm.201703976"]
