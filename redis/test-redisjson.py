import redis
import json

r = redis.Redis(host='gpuserver', port=6379, db=0)

data = {
    "session_1": {
        "parties": [
            {"id": 1, "shapley_values": [0.5, 0.5, 0.4, 0.3]},
            {"id": 2, "shapley_values": [0.6, 0.6, 0.5, 0.4]},
            {"id": 3, "shapley_values": [0.7, 0.7, 0.6, 0.5]}
        ]
    }
}

r.execute_command('JSON.SET', 'session_1', '.', json.dumps(data))

responseAll = r.execute_command('JSON.GET', 'session_1')
print('responseAll: {}'.format(responseAll.decode('utf-8')))

""" response = r.execute_command('JSON.GET', 'session_1', '.session_1.parties[2].shapley_values[2]')
print('response: {}'.format(response.decode('utf-8')))

r.execute_command('JSON.ARRAPPEND', 'session_1', '.session_1.parties[2].shapley_values', 1.8)

responseAll = r.execute_command('JSON.GET', 'session_1')
print('responseAll: {}'.format(responseAll.decode('utf-8')))
 """

""" from redis.commands.json.path import Path
from redis.commands.json import JSONCommands




key = 'session_1'
parties = (r.execute_command('JSON.GET', key, '.session_1.parties')).decode('utf-8')

parties = json.loads(parties)


if isinstance(parties, list) and all(isinstance(party, dict) for party in parties):
    index = next((i for i, party in enumerate(parties) if party['id'] == 1), None)
else:
    print('parties is not a list of dictionaries')
    index = None
print('index: {}'.format(index))

# New shapley values to set
new_shapley_values = [0.2, 0.3, 0.4]

if index is not None:
    #r.execute_command('JSON.ARRAPPEND', key, Path.rootPath().property('session_1').property('parties').index(index).property('shapley_values'), 2.8)
    #r.execute_command('JSON.ARRAPPEND', key, '.{}.parties[{}].shapley_values'.format(key, index), 3.8)
    r.execute_command('JSON.SET', key, '.{}.parties[{}].shapley_values'.format(key, index), json.dumps(new_shapley_values))
    
responseAll = r.execute_command('JSON.GET', key)
print('responseAll: {}'.format(responseAll.decode('utf-8'))) """

