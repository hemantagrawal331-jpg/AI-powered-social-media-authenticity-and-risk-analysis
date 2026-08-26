from app.intelligence.stats import (
    benford_chi_square,
    burstiness,
    coefficient_of_variation,
    expit,
    jaccard,
    jaro_winkler,
    levenshtein_similarity,
    logit,
    mad,
    median,
    normalized_entropy,
    robust_z,
    shannon_entropy,
)


def test_shannon_entropy_known_binary():
    assert abs(shannon_entropy("abab") - 1.0) < 1e-9


def test_normalized_entropy_bounds():
    assert 0 <= normalized_entropy("aaaa") <= 1
    assert normalized_entropy("abcdefgh") > normalized_entropy("aaaaaaa")


def test_mad_and_robust_z_outlier():
    pop = [10.0, 11.0, 9.0, 10.5, 10.2, 9.8, 10.1]
    assert mad(pop) > 0
    z = robust_z(40.0, pop)
    assert z > 5


def test_median_even():
    assert median([1, 2, 3, 4]) == 2.5


def test_cv_and_burstiness():
    regular = [5.0, 5.0, 5.0, 5.0, 5.0]
    bursty = [1.0, 1.0, 20.0, 1.0, 18.0]
    assert coefficient_of_variation(regular) < 0.05
    assert burstiness(bursty) > burstiness(regular)


def test_logit_expit_roundtrip():
    for p in (0.12, 0.5, 0.88):
        assert abs(expit(logit(p)) - p) < 1e-6


def test_benford_insufficient_sample_is_neutral():
    chi2, p_value, n = benford_chi_square([2, 3, 4])
    assert n < 10
    assert p_value == 1.0
    assert chi2 == 0.0


def test_string_similarity():
    assert jaro_winkler("official", "official") == 1.0
    assert levenshtein_similarity("nasa", "nasa") == 1.0
    assert jaccard({"a", "b"}, {"b", "c"}) == 1 / 3
