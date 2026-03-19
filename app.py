app.py                                                                         
from flask import Flask, jsonify
import socket
import os

app = Flask(__name__)
 
@app.route("/")
def home():
        return "Robot Fleet Manager is running!"

@app.route("/health")
def health():
        return jsonify(status="healthy")

@app.route("/info")
def info():
        return jsonify(
                hostname=socket.gethostname(),message= "This is a test microservice running on Kubernetes"
        )

if __name__ == "__main__":
        app.run(host="0.0.0.0",port=8080)






