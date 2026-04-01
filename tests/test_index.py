from pathlib import Path

from scripts.split_reports import generate_index_html


def test_index_html_created(tmp_path):
    keys = {("730", "2020"), ("730", "2019")}
    generate_index_html(keys, tmp_path)
    assert (tmp_path / "index.html").exists()


def test_appids_sorted_numerically(tmp_path):
    # "4000" must come after "730" numerically, not before it lexicographically
    keys = {("4000", "2021"), ("570", "2022"), ("730", "2020")}
    generate_index_html(keys, tmp_path)
    html = (tmp_path / "index.html").read_text()
    pos_570 = html.index("570/")
    pos_730 = html.index("730/")
    pos_4000 = html.index("4000/")
    assert pos_570 < pos_730 < pos_4000


def test_years_sorted_ascending(tmp_path):
    keys = {("730", "2022"), ("730", "2019"), ("730", "2021")}
    generate_index_html(keys, tmp_path)
    html = (tmp_path / "index.html").read_text()
    pos_2019 = html.index("2019.json")
    pos_2021 = html.index("2021.json")
    pos_2022 = html.index("2022.json")
    assert pos_2019 < pos_2021 < pos_2022


def test_year_links_correct_href(tmp_path):
    keys = {("730", "2020")}
    generate_index_html(keys, tmp_path)
    html = (tmp_path / "index.html").read_text()
    assert 'href="data/730/2020.json"' in html


def test_details_summary_structure(tmp_path):
    keys = {("730", "2020")}
    generate_index_html(keys, tmp_path)
    html = (tmp_path / "index.html").read_text()
    assert "<details>" in html
    assert "<summary>730/</summary>" in html


def test_generated_timestamp_present(tmp_path):
    keys = {("730", "2020")}
    generate_index_html(keys, tmp_path)
    html = (tmp_path / "index.html").read_text()
    assert "Generated:" in html
