from flask import Flask, request, jsonify
import os
import logging

logging.basicConfig(filename='./logs/app.log', level=logging.DEBUG)

app = Flask(__name__)
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
    logging.info("Session ID: {}, Party ID: {}, Epoch: {} ".format(session_id, party_id, epoch))

    if file and allowed_file(file.filename):
        filename = file.filename
        directory = os.path.join(UPLOAD_FOLDER, session_id, party_id, epoch)

        # Create directory if it does not exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        file.save(os.path.join(directory, filename))
        logging.info('File uploaded successfully: {}'.format(filename))
        return jsonify({"message": "File uploaded successfully", "filename": filename}), 200
    return jsonify({"error": "File type not allowed"}), 400

if __name__ == '__main__':
    app.run(debug=True)
