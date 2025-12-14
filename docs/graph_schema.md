# Graph Schema – Course Prerequisites Project

This document explains **what exists in the Neo4j graph** and **how it is connected**.

We use four main node labels:

- `Course`
- `Student`
- `Program`
- `Semester`

We use a few relationship types:

- `PRE_REQUIRES`
- `HAS_COMPLETED`
- `TAKES`
- `PART_OF`
- `OFFERED_IN`

---

## 1. Node Labels

### 1.1 `Course`

Represents a university course (e.g. `CS 125`, `MATH 241`).

**Properties**

- `code` (string, required, unique)  
  Example: `"CS 125"`
- `name` (string, optional)  
  Example: `"Introduction to Computer Science"`
- `credits` (integer, optional)  
  Example: `3`
- `department` (string, optional)  
  Example: `"CS"`

> In the CSV we currently only have `code`. Other fields can be added later.

---

### 1.2 `Student`

Represents a student.

**Properties**

- `student_id` (string, required, unique)  
  Example: `"s123456"`
- `name` (string, optional)  
  Example: `"Elise Deyris"`
- `program_name` (string, optional)  
  Example: `"BSc Computer Science"`
- `entry_year` (integer, optional)  
  Example: `2023`

---

### 1.3 `Program`

Represents a degree program.

**Properties**

- `name` (string, required, unique)  
  Example: `"BSc Computer Science"`
- `type` (string, optional)  
  Example: `"BSc"`, `"MSc"`
- `department` (string, optional)  
  Example: `"Engineering"`

---

### 1.4 `Semester`

Represents a semester in which courses are offered.

**Properties**

- `name` (string, required)  
  Example: `"Fall 2024"`
- `year` (integer, required)  
  Example: `2024`
- `index` (integer, required)  
  Example: `1` for Spring, `2` for Fall (or any convention you choose)

> We enforce uniqueness on `(year, index)` so you can’t create the same semester twice.

---

## 2. Relationship Types

### 2.1 `(:Course)-[:PRE_REQUIRES]->(:Course)`

Meaning:  
**Course A PRE_REQUIRES Course B**  
→ To take course A, you must have completed course B.

- Direction: `Course` **→** its **prerequisite course**
- Example:  
  `(:Course {code: "CS 225"})-[:PRE_REQUIRES]->(:Course {code: "CS 125"})`

This is what we build from the CSV file.

---

### 2.2 `(:Student)-[:HAS_COMPLETED]->(:Course)`

Meaning:  
The student has **already completed** this course in the past.

- Used to check if the student satisfies the prerequisites.
- Example:  
  `(:Student {student_id: "s1"})-[:HAS_COMPLETED]->(:Course {code: "CS 125"})`

---

### 2.3 `(:Student)-[:TAKES]->(:Course)`

Meaning:  
The student is **currently enrolled** in this course.

- Useful for validation: can the student take this course now?
- Example:  
  `(:Student {student_id: "s1"})-[:TAKES]->(:Course {code: "CS 225"})`

---

### 2.4 `(:Course)-[:PART_OF]->(:Program)`

Meaning:  
The course is part of a specific program.

- Example:  
  `(:Course {code: "CS 125"})-[:PART_OF]->(:Program {name: "BSc Computer Science"})`

---

### 2.5 `(:Course)-[:OFFERED_IN]->(:Semester)`

Meaning:  
The course is offered in a given semester.

- Example:  
  `(:Course {code: "CS 125"})-[:OFFERED_IN]->(:Semester {year: 2024, index: 1})`

---

## 3. Example Mini-Graph

One possible path in the graph:

```text
(Student) --HAS_COMPLETED--> (Course: CS 125)
   \
    \--TAKES--> (Course: CS 225) --PRE_REQUIRES--> (Course: CS 125)
