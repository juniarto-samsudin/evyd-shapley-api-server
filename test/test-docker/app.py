import time
import logging
import redis
from dotenv import load_dotenv
import os
import json

load_dotenv()
session_id = os.getenv('SESSION_ID')
log_name = 'container-{}.log'.format(session_id)
logging.basicConfig(filename=("./logs/container-logs/{}".format(log_name)), 
                    level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(message)s', 
                    datefmt='%m/%d/%Y %I:%M:%S %p')


#Get Redis Host from environment variable in docker-compose
#If not found, use localhost for development
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = os.getenv('REDIS_PORT', 6379)
logging.info('Redis Host: {}'.format(redis_host))
logging.info('Session ID: {}'.format(session_id))
r = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
def main():
    data = {
    "session_1": {
        "parties": [
            {"id": 1, "shapley_values": [0.5, 0.5, 0.4, 0.3]},
            {"id": 2, "shapley_values": [0.6, 0.6, 0.5, 0.4]},
            {"id": 3, "shapley_values": [0.7, 0.7, 0.6, 0.5]}
        ]}}
    r.execute_command('JSON.SET', 'session_1', '.', json.dumps(data))
    logging.info('Hello World!')
    time.sleep(10)

if __name__ == '__main__':
    main()

