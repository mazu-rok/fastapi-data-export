"""Start the app locally, or use --production for the production server."""
import argparse
import os
from dotenv import load_dotenv

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--production', action='store_true')
    options = parser.parse_args()
    load_dotenv(override=False)
    if options.production:
        os.environ['APP_ENV'] = 'production'
    host, port = os.getenv('HOST', '127.0.0.1'), int(os.getenv('PORT', '8000'))
    import uvicorn
    uvicorn.run('app:create_app', factory=True, host=host, port=port)
