import pytest

from real_estate.domain.model import Features, Media


def test_features_default_to_unknown() -> None:
    f = Features()
    assert f.has_lift is None
    assert f.get("has_pool") is None


def test_features_preserve_tri_state() -> None:
    f = Features(has_lift=True, has_garden=False)
    assert f.get("has_lift") is True
    assert f.get("has_garden") is False
    assert f.get("has_terrace") is None


def test_features_get_unknown_name_raises() -> None:
    with pytest.raises(KeyError):
        Features().get("has_helipad")


def test_media_accepts_absolute_urls() -> None:
    m = Media(images=("https://cdn.example/1.jpg",), videos=("http://v.example/a.mp4",))
    assert len(m.images) == 1


def test_media_rejects_relative_urls() -> None:
    with pytest.raises(ValueError):
        Media(images=("/relative/path.jpg",))


def test_media_defaults_are_empty() -> None:
    m = Media()
    assert m.images == ()
    assert m.videos == ()
