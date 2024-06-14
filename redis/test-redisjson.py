import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0)

data = {
    "session_1": {
        "parties": [
            {"id": 1, "shapley_values": [0.5, 0.5, 0.4, 0.3]},
            {"id": 2, "shapley_values": [0.6, 0.6, 0.5, 0.4]},
            {"id": 3, "shapley_values": [0.7, 0.7, 0.6, 0.5]}
        ]
    }
}

#r.execute_command('JSON.SET', 'session_1', '.', json.dumps(data))

responseAll = r.execute_command('JSON.GET', 'session_1')
print('responseAll: {}'.format(responseAll.decode('utf-8')))

""" response = r.execute_command('JSON.GET', 'session_1', '.session_1.parties[2].shapley_values[2]')
print('response: {}'.format(response.decode('utf-8')))

r.execute_command('JSON.ARRAPPEND', 'session_1', '.session_1.parties[2].shapley_values', 1.8)

responseAll = r.execute_command('JSON.GET', 'session_1')
print('responseAll: {}'.format(responseAll.decode('utf-8')))
 """