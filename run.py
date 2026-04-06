from dotenv import load_dotenv
load_dotenv()

from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug)
