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
    try:
        poem_maker(**data)
    except Exception as e:
        # TODO Fix this.. This is probably not the only fail case here
        return f'Couldn\'t find any unused ads meeting these specifications.'
    return f'Job completed: {str(data)}'


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
