import requests

url = 'http://127.0.0.1:5000/upload'
files = {'file': open('test.txt', 'rb')}
data = {'session_id': '12345', 'party_id': '67890', 'epoch': '1'}
response = requests.post(url, files=files, data=data)
print(response.json())

# Response:
#{'container': {'status': 'running'}, 'filename': 'test.txt', 'message': 'File uploaded successfully'}