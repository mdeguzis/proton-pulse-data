import json

from scripts.pipeline.most_played import build_most_played


def _write_index(tmp_path, rows):
    (tmp_path / "search-index.json").write_text(json.dumps(rows), encoding="utf-8")


def test_keeps_rated_games_in_rank_order_and_skips_untracked(tmp_path):
    _write_index(tmp_path, [
        ["730", "Counter-Strike 2", "gold", 78, 0],
        ["570", "Dota 2", "platinum", 50, 0],
    ])
    ranks = [
        {"appid": 570, "peak_in_game": 600000},
        {"appid": 12345, "peak_in_game": 500000},  # not in our index -> skipped
        {"appid": 730, "peak_in_game": 1200000},
    ]
    out = build_most_played(tmp_path, ranks=ranks)

    assert [g["appId"] for g in out] == [570, 730]  # rank order preserved
    assert out[0]["appId"] == 570
    assert out[0]["title"] == "Dota 2"
    assert out[0]["peak"] == 600000
    assert out[0]["rating"] == "platinum"
    assert out[0]["protondbCount"] == 50
    # file on disk matches the returned rows
    assert json.loads((tmp_path / "most_played.json").read_text(encoding="utf-8")) == out


def test_skips_unknown_or_missing_tier(tmp_path):
    _write_index(tmp_path, [["999", "Untested Game", "unknown", 0, 0]])
    out = build_most_played(tmp_path, ranks=[{"appid": 999, "peak_in_game": 100}])
    assert out == []


def test_respects_limit(tmp_path):
    _write_index(tmp_path, [[str(i), f"Game {i}", "gold", 1, 0] for i in range(20)])
    ranks = [{"appid": i, "peak_in_game": 1000 - i} for i in range(20)]
    out = build_most_played(tmp_path, limit=5, ranks=ranks)
    assert len(out) == 5


def test_handles_non_int_peak(tmp_path):
    _write_index(tmp_path, [["730", "CS2", "gold", 10, 0]])
    out = build_most_played(tmp_path, ranks=[{"appid": 730, "peak_in_game": None}])
    assert out[0]["appId"] == 730
    assert out[0]["title"] == "CS2"
    assert out[0]["peak"] is None
    assert out[0]["rating"] == "gold"
    assert out[0]["protondbCount"] == 10
