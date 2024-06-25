from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
import docker
from dotenv import load_dotenv
import redis
import json

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
app.config['HOST_CONTAINER_UPLOAD_PATH'] = os.getenv('HOST_CONTAINER_UPLOAD_PATH')
app.config['HOST_CONTAINER_VAL_PATH'] = os.getenv('HOST_CONTAINER_VAL_PATH')
app.config['SHAPLEYAPP_IMAGE'] = os.getenv('SHAPLEYAPP_IMAGE')

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
        r.hset("session:{}".format(session_id), mapping={
                        "party_ids": party_ids_json_str
                        })
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
            file.save(os.path.join(directory, filename))
            logging.info('File saved: {}'.format(filename))
        except Exception as e:
            logging.error('Failed to save file: {}'.format(str(e)))
            return jsonify({"error": "Failed to save file"}), 500

        # Start container
        #image = 'test-docker'
        image = app.config['SHAPLEYAPP_IMAGE']
        containerStatus = getContainerStatus(session_id)
        logging.info('Container status: {}'.format(containerStatus))
        # Launch only if container does not exist
        if containerStatus == None:
            logging.info('Container not found. Starting container...')
            #checking if session has been initiated and party ids are set
            party_ids_json_str = r.hget("session:{}".format(session_id), "party_ids")
            if party_ids_json_str == None:
                logging.error('Session not initiated. Skipping launching container operation ...')
                return jsonify({'error': 'Session not initiated. Skipping launching container operation ...'}), 500
            party_ids = json.loads(party_ids_json_str)

            # Acquiring Lock in Non-blocking mode, immediately return if lock is not available
            lock = r.lock("lock:{}".format(session_id), blocking=False, timeout=10) 
            try:
                with lock:
                    #container_id = launch_container(image, session_id)
                    container_id = launch_container2(image, session_id, party_ids)
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
    logging.info("get_shapley_values for sessionID: {}".format(session_id))
    try:
        response = r.execute_command('JSON.GET', session_id)
        if response is None:
            return "No data found four the given session ID: {}".format(session_id), 404
        return response
    except redis.RedisError as e:
        logging.error("Redis Error: {}".format(str(e)))
        return "Internal Server Error", 500

@app.route('/get-shapley-values-mock', methods=['GET'])
def get_shapley_values_mock():
    session_id = request.args.get('session_id')
    logging.info("get_shapley_values for sessionID: {}".format(session_id))
    try:
        response = r.execute_command('JSON.GET', 'session-1')
        if response is None:
            return "No data found four the given session ID: {}".format('session-1'), 404
        return response
    except redis.RedisError as e:
        logging.error("Redis Error: {}".format(str(e)))
        return "Internal Server Error", 500
    
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

def launch_container2(image, session_id, party_ids):
    """ 
    client1_dir = os.path.join(app.config['HOST_CONTAINER_UPLOAD_PATH'], session_id, party_ids[0])
    client2_dir = os.path.join(app.config['HOST_CONTAINER_UPLOAD_PATH'], session_id, party_ids[1])
    client3_dir = os.path.join(app.config['HOST_CONTAINER_UPLOAD_PATH'], session_id, party_ids[2])
    global_dir = os.path.join(app.config['HOST_CONTAINER_UPLOAD_PATH'], session_id, 'global') 
    """
    client1_dir = os.path.join(app.config['HOST_CONTAINER_UPLOAD_PATH'], 'local1' )
    client2_dir = os.path.join(app.config['HOST_CONTAINER_UPLOAD_PATH'], 'local2' )
    client3_dir = os.path.join(app.config['HOST_CONTAINER_UPLOAD_PATH'], 'local3' )
    global_dir = os.path.join(app.config['HOST_CONTAINER_UPLOAD_PATH'], 'global1' )
    logging.info('Client 1 Directory: {}'.format(client1_dir))
    logging.info('Client 2 Directory: {}'.format(client2_dir))
    logging.info('Client 3 Directory: {}'.format(client3_dir))
    logging.info('Global Directory: {}'.format(global_dir))
    logging.info('Validation Dataset Directory: {}'.format(app.config['HOST_CONTAINER_VAL_PATH']))
    try:
        container = client.containers.run(image, 
                                          detach=True,
                                          volumes={
                                              app.config['HOST_CONTAINER_LOGS_PATH']: {
                                                    'bind': '/app/logs',
                                                    'mode': 'rw'
                                                },
                                              client1_dir: {
                                                    'bind': '/app/local1',
                                                    'mode': 'rw'
                                                },
                                              client2_dir: {
                                                    'bind': '/app/local2',
                                                    'mode': 'rw'
                                                },
                                              client3_dir: {
                                                        'bind': '/app/local3',
                                                        'mode': 'rw'
                                                    },
                                              global_dir: {
                                                            'bind': '/app/global',
                                                            'mode': 'rw'
                                                        },
                                              app.config['HOST_CONTAINER_VAL_PATH']: {
                                                    'bind': '/app/valdataset',
                                                    'mode': 'rw'
                                                }  
                                          },
                                          environment={
                                              'LOCAL_MODEL_PATH1':'/app/local1',
                                              'LOCAL_MODEL_PATH2':'/app/local2',
                                              'LOCAL_MODEL_PATH3':'/app/local3',
                                              'GLOBAL_MODEL_PATH':'/app/global',
                                              'VALIDATION_DATASET':'/app/valdataset',
                                              'TZ': 'Asia/Singapore',
                                              #'REDIS_HOST': 'redis',
                                              'REDIS_HOST': '172.20.117.210',
                                              'SESSION_ID': session_id,
                                              'PARTY_ID0': party_ids[0],
                                              'PARTY_ID1': party_ids[1],
                                              'PARTY_ID2': party_ids[2],
                                              'REDIS_PORT': redis_port
                                          },
                                          device_requests=[
                                            docker.types.DeviceRequest(
                                                driver='nvidia',
                                                count=-1, 
                                                capabilities=[['gpu']]
                                                )
                                            ],
                                            shm_size='2gb',
                                            auto_remove=False,
                                            #network="evyd-shapley-api-server_shapley-network"
                                          )
        return container.id
    except docker.errors.ImageNotFound:
        logging.error('Image not found')
        return None
    except docker.errors.APIError as e:
        logging.error(str(e))
        return None    
if __name__ == '__main__':
    app.run(debug=True)
