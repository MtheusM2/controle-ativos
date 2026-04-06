from config import FLASK_DEBUG
from web_app.app import application as app


# Entry point de desenvolvimento. O deploy deve usar wsgi:app ou wsgi:application.


if __name__ == "__main__":
    app.run(debug=FLASK_DEBUG)
