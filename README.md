# University Course Prerequisite Planner

This project builds a graph of university courses and their prerequisites using Neo4j and exposes several useful FastAPI endpoints to explore the graph, detect cycles, and validate student eligibility for a course.

This README includes everything needed to run, and test the current version of the project.

---

## Project Structure (current)

```
knowledge_graphs_project/
│
├── backend/
│   ├── main.py
│   ├── database/
│   │   └── neo4j.py
│   └── services/
│       └── prerequisites.py
│
├── scripts/
│   └── seed_data.py
│
├── data/
│   └── courses.csv
│
├── docs/
│   └── graph_schema.md
│
└── README.md
```

---

# 1 - Installation

### Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

---

# 2 - Run Neo4j (Docker)

This project uses Neo4j **via Docker Compose**.

### Start Neo4j

```bash
docker compose up -d neo4j
```

Neo4j Browser:

👉 [http://localhost:7474](http://localhost:7474)

**Default credentials:**

* **Username:** `neo4j`
* **Password:** `password`

---

# 3 - Seed the Database

The project includes a script to insert:

* Course nodes
* PRE_REQUIRES relationships
* Constraints and indexes

### **Run the seed script**

```bash
source .venv/bin/activate
python scripts/seed_data.py
```

You should see output similar to:

```
Creating constraints...
Loading CSV...
Inserted 500 courses
 Inserted 350 prerequisite edges
```

You can verify in Neo4j Browser:

```cypher
MATCH (c:Course) RETURN count(c);
MATCH (c)-[:PRE_REQUIRES]->(p) RETURN c, p LIMIT 20;
```

---

# 4 - Run the API

Start the FastAPI server:

```bash
uvicorn backend.main:app --reload --port 8001
```

Test in browser:

👉 [http://127.0.0.1:8001/health](http://127.0.0.1:8001/health)

Expected response:

```json
{"status": "ok", "neo4j_ok": true}
```

---

# 5 - API Endpoints

## Health Check

`GET /health`

Confirms both API and Neo4j are running.

---

## Get Prerequisites of a Course

`GET /courses/{course_code}/prerequisites?all=true`

* `all=true` → recursive prerequisites
* `all=false` → direct prerequisites

Example:

```
/courses/AAS%20211/prerequisites?all=true
```

---

## Get All Cycles in the Graph

`GET /courses/cycles`

Detects loops in the prerequisite structure.

---

## Validate If a Student Can Take a Course

`POST /validation/prerequisites`

### Body:

```json
{
  "target_course": "AAS 211",
  "completed_courses": ["AAS 100", "AAS 120"]
}
```

### Success Response Example:

```json
{
  "course": "AAS 211",
  "can_take": true,
  "required_prerequisites": ["AAS 100", "AAS 120"],
  "missing_prerequisites": [],
  "completed_courses": ["AAS 100", "AAS 120"]
}
```

### Missing Prerequisites Example:

```json
{
  "course": "AAS 211",
  "can_take": false,
  "required_prerequisites": ["AAS 100", "AAS 120"],
  "missing_prerequisites": ["AAS 120"],
  "completed_courses": ["AAS 100"]
}
```

---

# 6 - Graph Schema

A detailed schema is available here:

 `docs/graph_schema.md`

It includes:

* Node types (`Course`, `Student`, `Program`, `Semester`)
* Relationship types (`PRE_REQUIRES`, `HAS_COMPLETED`, etc.)
* Constraints and indexes
* Example graph structures

---
# 7 – Graph Data Science (GDS)

This project leverages the **Neo4j Graph Data Science (GDS) library** to perform in-memory graph analytics on the university course prerequisite network.

The objective is to go beyond simple graph traversal queries and extract **structural insights** from the curriculum graph, such as:
- identifying foundational and high-impact courses,
- detecting prerequisite bottlenecks,
- analyzing dependency chains between courses.

---

### 7.1 In-memory Graph Projection

Before running Graph Data Science algorithms, the course graph is projected into memory.

- **Node label**: `Course`
- **Relationship type**: `PRE_REQUIRES`
- **Orientation**: `NATURAL` (directed from prerequisite → course)

Cypher query used for the projection:

```cypher
CALL gds.graph.project(
  'courseGraph',
  'Course',
  {
    PRE_REQUIRES: {
      orientation: 'NATURAL'
    }
  }
);

---

# Status for the moment 

| Component                  |Status|
| -------------------------- | -----|
| Neo4j driver setup         | Done |
| Data seeding               | Done |
| Constraints + indexes      | Done |
| Graph schema               | Done |
| Core Cypher queries        | Done |
| Prerequisite validation    | Done |
| Cycle detection            | Done |
| API endpoints              | Done |
| README basic documentation | Done |

---
