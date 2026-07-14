import pytest 
from services.watchlist_service import add_to_watchlist
from services.collection_service import FilmNotFoundError

def test_add_to_watchlist_nonexistent_film_raises(app, sample_user):

    """
    Adding a film_id that doesn't exist in the database should raise
    FilmNotFoundError, not a database integrity error.
    """
    with app.app_context():
        fake_film_id = 999999

        with pytest.raises(FilmNotFoundError):
            add_to_watchlist(user_id=sample_user, film_id=fake_film_id)