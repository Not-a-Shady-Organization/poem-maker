from flask import Flask, request
from poem_maker import poem_maker
import os

app = Flask(__name__)

@app.route('/',  methods=['GET'])
def hello_world():
    return 'Poem Maker is live :)'

@app.route('/', methods=['POST'])
def kickoff_poem_maker():
    data = request.get_json()
    poem_maker(**data)
    return f'Job received: {str(data)}'


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
