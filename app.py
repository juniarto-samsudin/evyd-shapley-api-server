from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
import docker
from dotenv import load_dotenv
import redis

client = docker.from_env()
load_dotenv()

#Get Redis Host from environment variable in docker-compose
#If not found, use localhost for development
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = os.getenv('REDIS_PORT', 6379)
r = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
logging.basicConfig(filename='./logs/app.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s', 
                    datefmt='%m/%d/%Y %I:%M:%S %p')

app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
app.config['HOST_CONTAINER_LOGS_PATH'] = os.getenv('HOST_CONTAINER_LOGS_PATH')

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'tar'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            file.save(os.path.join(directory, filename))
            logging.info('File saved: {}'.format(filename))
        except Exception as e:
            logging.error('Failed to save file: {}'.format(str(e)))
            return jsonify({"error": "Failed to save file"}), 500

        # Start container
        image = 'test-docker'
        containerStatus = getContainerStatus(session_id)
        logging.info('Container status: {}'.format(containerStatus))
        # Launch only if container does not exist
        if containerStatus == None:
            logging.info('Container not found. Starting container...')
            # Acquiring Lock in Non-blocking mode, immediately return if lock is not available
            lock = r.lock("lock:{}".format(session_id), blocking=False, timeout=10) 
            try:
                with lock:
                    container_id = launch_container(image, session_id)
                    if container_id:
                        r.hset("session:{}".format(session_id), mapping={
                            "container_status": "running", 
                            "container_id": container_id})
                        logging.info('Container started: {}'.format(container_id))
                        return jsonify({"message": "File uploaded successfully", 
                                    "filename": filename,
                                    "container": {"status": "running", "id": container_id}
                                    }), 200
                    else:
                        logging.error('Failed to start container')
                        return jsonify({
                                    'message': 'File uploaded successfully',
                                    'filename': filename,
                                    'error': 'Failed to start container'
                                    }), 500
            except redis.exceptions.LockError:
                logging.error('Failed to acquire lock')
                return jsonify({'error': 'Failed to acquire lock. Skipping launching container operation ...'}), 500
        else:
            logging.info('Container found. Skipping launching container operation ...')
            return jsonify({"message": "File uploaded successfully", 
                            "filename": filename,
                            "container": {"status": containerStatus}
                            }), 200
    return jsonify({"error": "File type not allowed"}), 400

@app.route('/start-container', methods=['POST'])
def start_container():
    image = request.json.get('image')
    if not image:
        return jsonify({'error': 'Image name is required'}), 400
    
    try:
        container = client.containers.run(image, 
                                          detach=True,
                                          volumes={
                                              app.config['HOST_CONTAINER_LOGS_PATH']: {
                                                    'bind': '/app/logs',
                                                    'mode': 'rw'
                                                }
                                          },
                                          environment={
                                              'TZ': 'Asia/Singapore'
                                          })
        return jsonify({'message': 'Container started', 'container_id': container.id})
    except docker.errors.ImageNotFound:
        return jsonify({'error': 'Image not found'}), 404
    except docker.errors.APIError as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-shapley-values', methods=['GET'])
def get_shapley_values():
    session_id = request.args.get('session_id')
    logging.info("get_shapley_values for sessionID: ".format(session_id))
    response = r.execute_command('JSON.GET', 'session_1')
    return response
    
def launch_container(image, session_id):
    try:
        container = client.containers.run(image, 
                                          detach=True,
                                          volumes={
                                              app.config['HOST_CONTAINER_LOGS_PATH']: {
                                                    'bind': '/app/logs',
                                                    'mode': 'rw'
                                                }
                                          },
                                          environment={
                                              'TZ': 'Asia/Singapore',
                                              'REDIS_HOST': 'redis',
                                              'SESSION_ID': session_id,
                                              'REDIS_PORT': redis_port
                                          },
                                            auto_remove=False,
                                            network="evyd-shapley-api-server_shapley-network"
                                          )
        return container.id
    except docker.errors.ImageNotFound:
        logging.error('Image not found')
        return None
    except docker.errors.APIError as e:
        logging.error(str(e))
        return None
    
def getContainerStatus(session_id):
    container_status = r.hget("session:{}".format(session_id), "container_status")
    return container_status
    
if __name__ == '__main__':
    app.run(debug=True)
