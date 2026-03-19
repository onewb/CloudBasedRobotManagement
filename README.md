# Cloud-Based Robot Management System

## 📌 Project Overview

This project implements a cloud-native robot fleet management system using a simulated environment to demonstrate how autonomous robots can be coordinated at scale using modern cloud infrastructure.

The system simulates multiple robots that continuously send telemetry data and receive commands in real time through a distributed messaging architecture. The goal is to evaluate how scalable cloud services can support robot fleet coordination under varying workloads.

---

## 🏗️ Architecture

The system is built using Google Cloud services:

- Robot Simulator → Publishes telemetry data
- Pub/Sub → Messaging backbone
- Microservices → Process robot data
- Kubernetes Engine → Container orchestration and scaling
- Load Balancer → Exposes services externally

---

## ☁️ Google Cloud Services Used

- Google Kubernetes Engine (GKE) – Container orchestration for microservices and simulators
- Pub/Sub – Real-time messaging between robots and cloud services
- Cloud Build – Container image building and deployment
- Artifact Registry – Stores Docker images
- Cloud Monitoring (planned) – Observability and performance tracking
- BigQuery (planned) – Analytics on robot telemetry data
- Memorystore (planned) – Low-latency caching layer

---

## 🤖 Robot Simulator

The robot simulator generates artificial telemetry data:

- Random robot positions (0–100 grid)
- Random status: idle, moving, working
- Sends data every 2 seconds

It also listens for command messages such as:
- MOVE_FORWARD
- STOP
- TURN_LEFT

### Key Features:
- Multi-threaded execution (telemetry + command listener)
- Real-time Pub/Sub communication
- Scalable design for multiple robot instances

---

## 🧪 Example Telemetry Payload

```json
{
  "robot_id": "robot-1",
  "position": [45, 78],
  "status": "moving"
}