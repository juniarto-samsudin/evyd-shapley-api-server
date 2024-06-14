import redis

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

r.hset("session:1", mapping={
                    "container_status": "running", 
                    "container_id": "12345"})

container_status = r.hget("session:1", "container_status")
container_id = r.hget("session:1", "container_id")
print(container_status, container_id)

#getall
session = r.hgetall("session:1")
print(session) #{'container_status': 'running', 'container_id': '12345'}

#update
r.hset("session:1", "container_status", "stopped")
status = r.hget("session:1", "container_status")
print(status) #stopped

container_status2 = r.hget("session:200", "container_status")
print(container_status2) #None
