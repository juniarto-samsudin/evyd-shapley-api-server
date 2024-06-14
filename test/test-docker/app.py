import time
import logging
import redis
from dotenv import load_dotenv
import os
import json


logging.basicConfig(filename='./logs/app.log', level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(message)s', 
                    datefmt='%m/%d/%Y %I:%M:%S %p')
load_dotenv()

#Get Redis Host from environment variable in docker-compose
#If not found, use localhost for development
redis_host = os.getenv('REDIS_HOST', 'localhost')
logging.info('Redis Host: {}'.format(redis_host))
r = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)
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

