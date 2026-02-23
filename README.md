# 📦 Delivery Zone Authorization Engine

A scalable geospatial engine that determines in real-time whether a delivery driver is authorized to accept an order inside a defined delivery zone.


## 🚀 Overview

Modern delivery platforms (food, e-commerce, logistics) must instantly determine whether a driver is eligible to accept an order based on their geographic location.

This project implements a spatial authorization engine using:

Computational geometry (Point-in-Polygon)

Spatial indexing (GiST / R-tree)

PostGIS

FastAPI

Scalable simulation (100k drivers)

## 🧠 Problem Statement

Given:

A set of delivery zones (Polygons)

A driver location (Point)

We must determine:

Is the driver located inside an authorized delivery zone?

This requires a topological spatial operation:


Point∈Polygon

Implemented via ST_Contains (PostGIS) or contains() (Shapely).


## 🗺 Spatial Concepts Used

Point-in-Polygon (Ray Casting algorithm)

Spatial indexing (GiST)

Coordinate Reference Systems (WGS84)

Geometry vs Geography types

Performance optimization for large-scale queries

## 🏗 Architecture

Client
  ↓
FastAPI Backend
  ↓
PostGIS Database
  ↓
Spatial Index (GiST)

## 🛠 Tech Stack

Python 3.x

FastAPI

PostgreSQL

PostGIS

Shapely

GeoPandas

Docker

Folium (Visualization)

## 🗄 Database Schema

CREATE TABLE delivery_zones (
    id SERIAL PRIMARY KEY,
    name TEXT,
    geom GEOMETRY(POLYGON, 4326)
);

CREATE TABLE drivers (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(POINT, 4326)
);

### Spatial index:

CREATE INDEX idx_zones_geom
ON delivery_zones
USING GIST (geom);

## 🌐 API Example

### Endpoint

POST /authorize

### Request
{
  "driver_id": 102,
  "latitude": -1.2921,
  "longitude": 36.8219
}

### Response

{
  "authorized": true,
  "zone": "CBD"
}

## 📊 Performance Benchmark

| Scenario        | Query Time |
| --------------- | ---------- |
| No Index        | 480 ms     |
| With GiST Index | 12 ms      |


### Tested with:

100,000 simulated drivers

20 delivery zones

## 🗺 Visualization

Interactive map displaying:

Delivery zones

Driver positions

Authorization result

Built using Folium.

## 🧪 Simulation

Random spatial generation of drivers

Stress-testing spatial queries

Performance comparison (indexed vs non-indexed)

## 🤖 Advanced Features (Optional Extensions)

Demand heatmap (DBSCAN clustering)

Dynamic zones (time-based restrictions)

Congestion-aware zones

Driver anomaly detection

Zone optimization using spatial statistics

## 📈 What This Project Demonstrates

Computational geometry knowledge

Spatial database design

Backend API development

Query optimization

Large-scale simulation

Geospatial data engineering

## 🐳 Running the Project
docker-compose up --build

### Access API at:
http://localhost:8000/docs

## 📂 Project Structure


## 🎯 Future Improvements

Move to Geography type for Earth curvature precision

Add caching layer (Redis)

Deploy on AWS (RDS + ECS)

Add real-time streaming (Kafka)

Integrate OpenStreetMap live data

## 📌 Real-World Applications

Food delivery platforms

Ride-sharing apps

Logistics & fleet management

Urban mobility analytics

Smart city monitoring

## 🏆 Author

francky Shakespeare GBANDI
Geospatial Data Science & sofware engineer 