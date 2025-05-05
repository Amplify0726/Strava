from flask import Flask
from webhook import webhook_bp

app = Flask(__name__)
app.register_blueprint(webhook_bp)

if __name__ == '__main__':
	app.run()
