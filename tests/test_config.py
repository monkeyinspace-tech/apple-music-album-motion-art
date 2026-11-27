import glob, json, os
from conftest import ROOT
import check_config


def test_all_templates_valid():
    files = glob.glob(os.path.join(ROOT, 'configs', 'templates', '*.json')) + [os.path.join(ROOT, 'examples', 'demo', 'demo_config.json')]
    assert files
    for f in files:
        errs, _ = check_config.check(json.load(open(f, encoding='utf-8')))
        assert not errs, (f, errs)


def test_detects_bad_box_and_point():
    errs, _ = check_config.check({'title': {'box': [500, 500, 100, 100]}, 'impact': [3000, 10]})
    assert any('title.box' in e for e in errs)
    assert any('impact' in e for e in errs)


def test_warns_unknown_key_and_large_key_content():
    errs, warns = check_config.check({'foo': 1, 'key_content_y': [0, 1800]})
    assert not errs
    assert any('foo' in w for w in warns)
    assert any('key_content_y' in w for w in warns)


def test_leak_colors_range():
    errs, _ = check_config.check({'leak_colors': [[0, 0, 300], [1, 2, 3]]})
    assert errs
