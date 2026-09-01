from app.intelligence.ood import combine_ood, feature_distance


def test_identical_vector_has_low_distance():
    vector = [1.0, 2.0, 3.0]
    assert feature_distance(vector, vector, [1.0, 1.0, 1.0]) < 0.05


def test_far_vector_has_high_distance():
    vector = [40.0, 40.0, 40.0]
    means = [1.0, 1.0, 1.0]
    stds = [1.0, 1.0, 1.0]
    assert feature_distance(vector, means, stds) > 0.8


def test_combine_ood_respects_missing_anomaly():
    score = combine_ood(anomaly=None, feature_dist=0.2, missing_ratio=0.8)
    assert 0.2 < score < 0.9
