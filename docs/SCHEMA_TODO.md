# What's Missing in the Graph Schema

## ✅ What You Have Now

- **Course nodes** - Created from CSV
- **PRE_REQUIRES relationships** - Created from CSV
- **Queries** - All prerequisite queries work

## ❌ What's Missing

### 1. Student Nodes
**Why:** Needed for `check_student_can_take()` to work with real students.

**What to create:**
```cypher
CREATE (s:Student {student_id: "s123", name: "John Doe"})
```

**Constraint needed:**
```cypher
CREATE CONSTRAINT student_id_unique IF NOT EXISTS
FOR (s:Student) REQUIRE s.student_id IS UNIQUE
```

---

### 2. HAS_COMPLETED Relationships
**Why:** Links students to courses they've finished.

**What to create:**
```cypher
MATCH (s:Student {student_id: "s123"})
MATCH (c:Course {code: "CS 125"})
CREATE (s)-[:HAS_COMPLETED]->(c)
```

---

### 3. Other Stuff (Optional for now)

- **Program nodes** - For degree programs
- **Semester nodes** - For scheduling
- **TAKES relationships** - For current enrollment
- **PART_OF relationships** - Link courses to programs
- **OFFERED_IN relationships** - Link courses to semesters

---

## Quick Start: Make It Work

To get `check_student_can_take()` working, you just need:

1. Create a Student node
2. Create HAS_COMPLETED relationships

That's it! Everything else can wait.

---

## Example: Create a Test Student

```cypher
// Create student
CREATE (s:Student {student_id: "s1", name: "Test Student"})

// Mark courses as completed
MATCH (s:Student {student_id: "s1"})
MATCH (c:Course {code: "CS 125"})
CREATE (s)-[:HAS_COMPLETED]->(c)
```

Then test: `GET /students/s1/can_take/CS 225`
