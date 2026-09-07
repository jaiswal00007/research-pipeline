from pipeline.models import RawSource, TopicCandidate, RepoInfo, TopicScore

def test_raw_source_fields():
    s = RawSource(
        url="https://github.com/foo/bar",
        title="foo",
        source_type="github",
        fetched_at="2026-09-07T00:00:00",
        raw={},
    )
    assert s.source_type == "github"

def test_topic_score_total():
    ts = TopicScore(
        usefulness=8, novelty=7, dev_value=9,
        search_demand=6, monetization=5, ease_demo=10
    )
    assert ts.total == 45

def test_repo_info_optional_fields():
    r = RepoInfo(full_name="foo/bar", url="https://github.com/foo/bar", stars=100)
    assert r.license is None
    assert r.install_works is None
