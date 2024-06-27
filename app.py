from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
import docker
from dotenv import load_dotenv
import redis
import json

#client = docker.from_env()
load_dotenv()

#Get Redis Host from environment variable in docker-compose
#If not found, use localhost for development
#redis_host = os.getenv('REDIS_HOST', 'localhost')
#redis_port = os.getenv('REDIS_PORT', 6379)
#r = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
logging.basicConfig(filename='./logs/app.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s', 
                    datefmt='%m/%d/%Y %I:%M:%S %p')

app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
app.config['HOST_CONTAINER_LOGS_PATH'] = os.getenv('HOST_CONTAINER_LOGS_PATH')
app.config['HOST_CONTAINER_UPLOAD_PATH'] = os.getenv('HOST_CONTAINER_UPLOAD_PATH')
app.config['HOST_CONTAINER_VAL_PATH'] = os.getenv('HOST_CONTAINER_VAL_PATH')
app.config['SHAPLEYAPP_IMAGE'] = os.getenv('SHAPLEYAPP_IMAGE')
app.config['SHAPLEYJSON_FOLDER'] = os.getenv('SHAPLEYJSON_FOLDER')

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'tar'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/initiate-session', methods=['POST'])
def initiate_session():
    data = request.json
    session_id = data.get('session_id')
    party_ids = data.get('party_id')
    logging.info("Initiating session: {}".format(session_id))
    logging.info("Party IDs: {}".format(party_ids))
    if not session_id:
        return jsonify({'error': 'Session ID is required'}), 400
    if not isinstance(party_ids, list):
        return jsonify({'error': 'Party IDs should be a list'}), 400
    try:
        party_ids_json_str = json.dumps(party_ids)
        logging.info("Party IDs String: {}".format(party_ids_json_str))
        '''
        r.hset("session:{}".format(session_id), mapping={
                        "party_ids": party_ids_json_str
                        })
        '''
        #Create Local and Global Directories
        for party_id in party_ids:
            directory = os.path.join(UPLOAD_FOLDER, session_id, party_id)
            if not os.path.exists(directory):
                os.makedirs(directory)
        directory = os.path.join(UPLOAD_FOLDER, session_id, 'global')
        if not os.path.exists(directory):
            os.makedirs(directory)
        return jsonify({'message': 'Session initiated', 'session_id': session_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        logging.error("No file part")
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        logging.error("No selected file")
        return jsonify({"error": "No selected file"}), 400
    
    session_id = request.form.get('session_id', 'Unknown')
    party_id = request.form.get('party_id', 'Unknown')
    epoch = request.form.get('epoch', 'Unknown')
    #local_model = 1 ==> if local model is uploaded
    #local_model = 0 ==> if global model is uploaded
    #default is local model
    local_model = request.form.get('local_model', '1')
    logging.info("Session ID: {}, Party ID: {}, Epoch: {} ".format(session_id, party_id, epoch))

    if file and allowed_file(file.filename):
        filename = file.filename
        parts = filename.split('.', 1)
        filename = "{}{}.{}".format(parts[0], epoch, parts[1])
        #filename = 'OK-{}-{}-{}'.format(session_id, party_id, filename)
        directory = None
        if local_model == '1': #local model
            directory = os.path.join(UPLOAD_FOLDER, session_id, party_id)
            logging.info('Directory for Local Model: {}'.format(directory))
        else: #global model
            directory = os.path.join(UPLOAD_FOLDER, session_id, 'global')
            logging.info('Directory for Global Model: {}'.format(directory))

        # Create directory if it does not exist
        if not os.path.exists(directory):
            os.makedirs(directory)
        try:
            file_path=os.path.join(directory, filename)
            file.save(file_path)
            logging.info('File saved: {}'.format(filename))

             # Rename the file to end with .done
            done_filename = "{}.done".format(filename)
            done_file_path = os.path.join(directory, done_filename)
            os.rename(file_path, done_file_path)
            logging.info('File renamed to: {}'.format(done_filename))
            return jsonify({"message": "File uploaded successfully", 
                            "filename": filename})
        except Exception as e:
            logging.error('Failed to save file: {}'.format(str(e)))
            return jsonify({"error": "Failed to save file"}), 500

    return jsonify({"error": "File type not allowed"}), 400


@app.route('/get-shapley-values', methods=['GET'])
def get_shapley_values():
    session_id = request.args.get('session_id')
    logging.info("get_shapley_values for sessionID: {}".format(session_id))
    try:
        # Define the path to search for the file
        directory = app.config['SHAPLEYJSON_FOLDER']
        logging.info("Directory: {}".format(directory))

        # Search for the file named after session_id
        file_path = None
        for file_name in os.listdir(directory):
            if file_name.startswith(session_id):
                file_path = os.path.join(directory, file_name)
                logging.info("File found: {}".format(file_path))
                break

        if file_path is None:
            return jsonify({"error": "No data found for the given session ID: {}".format(session_id)}), 404

        # Read the JSON content from the file
        with open(file_path, 'r') as file:
            response = json.load(file)
            logging.info("Response: {}".format(response))

        return jsonify(response)

    except Exception as e:
        logging.error("Error: {}".format(str(e)))
        return jsonify({"error": "get-shapley-values for {} error".format(session_id)}), 500
    
if __name__ == '__main__':
    app.run(debug=True)
