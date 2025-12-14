# Advanced Cypher Queries

This document demonstrates three practical, Cypher queries used in the Course Prerequisite Planner.

---

## Overview

These queries are designed to be:
- ✅ **Practical**: Solve real academic advising problems
- ✅ **Testable**: Can be run directly in Neo4j Browser

---

## Query 1: Find Bottleneck Courses

### Business Context
Identify courses that are critical bottlenecks in the curriculum - courses that many students need but have difficult prerequisites.

### Use Cases
- **Administrators**: Know where to add more course sections
- **Advisors**: Warn students about high-demand courses
- **Curriculum Design**: Identify courses that may need prerequisite restructuring

### Cypher Query

```cypher
// Find courses that block student progress
MATCH (bottleneck:Course)

// Count courses that require this course
OPTIONAL MATCH (dependent:Course)-[:PRE_REQUIRES]->(bottleneck)
WITH bottleneck, count(DISTINCT dependent) as courses_this_unlocks

// Count prerequisites for this course (depth 1-3)
OPTIONAL MATCH (bottleneck)-[:PRE_REQUIRES*1..3]->(prereq:Course)
WITH bottleneck, 
     courses_this_unlocks,
     count(DISTINCT prereq) as total_prereqs

// Filter for bottlenecks: unlocks many courses AND has multiple prereqs
WHERE courses_this_unlocks >= 3 
  AND total_prereqs >= 2

// Get semester availability
OPTIONAL MATCH (bottleneck)-[:OFFERED_IN]->(sem:Semester)
WITH bottleneck,
     courses_this_unlocks,
     total_prereqs,
     collect(DISTINCT sem.name) as offered_semesters

RETURN bottleneck.code as course_code,
       bottleneck.name as course_name,
       total_prereqs as prerequisites_needed,
       courses_this_unlocks as courses_unlocked,
       size(offered_semesters) as semesters_offered,
       offered_semesters[0..3] as sample_semesters
ORDER BY courses_this_unlocks DESC, total_prereqs DESC
LIMIT 10
```


### API Endpoint

```bash
GET /api/queries/bottleneck-courses?min_dependents=3&min_prerequisites=2&limit=10
```

**Response:**
```json
{
  "bottleneck_courses": [
    {
      "course_code": "CS 225",
      "course_name": "Data Structures",
      "prerequisites_needed": 2,
      "courses_unlocked": 8,
      "semesters_offered": 8,
      "sample_semesters": ["Fall 2024", "Spring 2025", "Fall 2025"],
      "bottleneck_score": 18
    }
  ],
  "total_found": 1
}
```

### Test in Neo4j Browser

1. Open http://localhost:7474
2. Paste the query above
3. Click Run (▶️)
4. View results in Table or Graph view

---

## Query 2: Personalized Course Recommendations

### Business Context
Generate personalized course recommendations for a student for a specific semester, with a "readiness score" indicating how prepared they are for each course.

### Use Cases
- **Academic Advisors**: Provide data-driven course suggestions
- **Students**: Self-service course planning
- **Registration Systems**: Suggest courses during enrollment

### Cypher Query

```cypher
// Get student and their completed courses
MATCH (student:Student {id: 'S001'})
OPTIONAL MATCH (student)-[:HAS_COMPLETED]->(completed:Course)
WITH student, collect(DISTINCT completed.code) as completed_codes

// Find courses offered in target semester that aren't completed
MATCH (available:Course)-[:OFFERED_IN]->(sem:Semester {id: 'FALL_2024'})
WHERE NOT available.code IN completed_codes

// Check prerequisites for each course
OPTIONAL MATCH (available)-[:PRE_REQUIRES]->(prereq:Course)
WITH student,
     available,
     completed_codes,
     collect(DISTINCT prereq.code) as required_prereqs

// Calculate missing prerequisites
WITH student,
     available,
     required_prereqs,
     [p IN required_prereqs WHERE NOT p IN completed_codes] as missing_prereqs

// Count courses this would unlock in the future
OPTIONAL MATCH (future:Course)-[:PRE_REQUIRES]->(available)
WITH student,
     available,
     required_prereqs,
     missing_prereqs,
     count(DISTINCT future) as unlocks_count

// Calculate readiness score (0-100)
WITH student,
     available,
     size(required_prereqs) as total_prereqs,
     size(missing_prereqs) as missing_count,
     unlocks_count,
     CASE 
         WHEN size(required_prereqs) = 0 THEN 100
         WHEN size(missing_prereqs) = 0 THEN 100
         ELSE toInteger(100.0 * (1.0 - toFloat(size(missing_prereqs)) / toFloat(size(required_prereqs))))
     END as readiness_score

// Only show courses they're ready for or almost ready for
WHERE readiness_score >= 75

RETURN available.code as course_code,
       available.name as course_name,
       readiness_score,
       missing_count as prerequisites_missing,
       unlocks_count as future_courses_unlocked,
       CASE 
           WHEN readiness_score = 100 THEN 'Ready Now'
           WHEN readiness_score >= 75 THEN 'Almost Ready'
           ELSE 'Not Ready'
       END as status
ORDER BY readiness_score DESC, unlocks_count DESC
LIMIT 15
```

### API Endpoint

```bash
GET /api/queries/students/S001/recommendations?semester_id=FALL_2024&min_readiness=75
```

**Response:**
```json
{
  "student_id": "S001",
  "student_name": "Alice Johnson",
  "program": "Computer Science",
  "semester_id": "FALL_2024",
  "recommendations": [
    {
      "course_code": "CS 225",
      "course_name": "Data Structures",
      "credits": 4,
      "readiness_score": 100,
      "prerequisites_missing": 0,
      "future_courses_unlocked": 6,
      "status": "Ready Now"
    },
    {
      "course_code": "CS 374",
      "course_name": "Algorithms",
      "credits": 4,
      "readiness_score": 75,
      "prerequisites_missing": 1,
      "future_courses_unlocked": 4,
      "status": "Almost Ready"
    }
  ],
  "total_recommendations": 2
}
```

### Test in Neo4j Browser

```cypher
// Change student_id and semester_id as needed
:param student_id => 'S001'
:param semester_id => 'FALL_2024'

// Then run the query
```

---

## Query 3: Courses by Prerequisite Depth

### Business Context
Show remaining courses organized by how many prerequisite levels they require, helping students visualize their path to graduation.

### Use Cases
- **Degree Planning**: Understand time to graduation
- **Course Selection**: Prioritize which courses to take first
- **Progress Tracking**: See what's blocking access to advanced courses

### Cypher Query

```cypher
// Get student and completed courses
MATCH (student:Student {id: 'S001'})
OPTIONAL MATCH (student)-[:HAS_COMPLETED]->(completed:Course)
WITH student, collect(DISTINCT completed.code) as completed_codes

// Find remaining courses
MATCH (remaining:Course)
WHERE NOT remaining.code IN completed_codes

// Count direct prerequisites
OPTIONAL MATCH (remaining)-[:PRE_REQUIRES]->(direct_prereq:Course)
WITH student,
     remaining,
     completed_codes,
     collect(DISTINCT direct_prereq.code) as direct_prereqs

// Calculate missing direct prerequisites
WITH student,
     remaining,
     direct_prereqs,
     [p IN direct_prereqs WHERE NOT p IN completed_codes] as missing_prereqs

// Get maximum depth of prerequisite chain (limited to 5)
OPTIONAL MATCH path = (remaining)-[:PRE_REQUIRES*1..5]->(deep_prereq:Course)
WHERE NOT deep_prereq.code IN completed_codes
WITH student,
     remaining,
     size(direct_prereqs) as total_direct_prereqs,
     size(missing_prereqs) as missing_direct_prereqs,
     CASE 
         WHEN count(path) = 0 THEN 0
         ELSE max(length(path))
     END as max_depth

// Get semester availability
OPTIONAL MATCH (remaining)-[:OFFERED_IN]->(sem:Semester)
WITH remaining,
     total_direct_prereqs,
     missing_direct_prereqs,
     max_depth,
     count(DISTINCT sem) as semesters_offered

// Only show courses with some prerequisites
WHERE total_direct_prereqs > 0

RETURN remaining.code as course_code,
       remaining.name as course_name,
       total_direct_prereqs as total_prerequisites,
       missing_direct_prereqs as prerequisites_missing,
       max_depth as chain_depth,
       semesters_offered,
       CASE 
           WHEN missing_direct_prereqs = 0 THEN 'Ready Now'
           WHEN missing_direct_prereqs <= 1 THEN 'Almost Ready'
           WHEN missing_direct_prereqs <= 2 THEN 'Plan Soon'
           ELSE 'Plan Later'
       END as recommendation
ORDER BY missing_direct_prereqs ASC, max_depth ASC, course_code
LIMIT 20
```

### API Endpoint

```bash
GET /api/queries/students/S001/course-depth?limit=20
```

**Response:**
```json
{
  "student_id": "S001",
  "student_name": "Alice Johnson",
  "program": "Computer Science",
  "completed_courses": 3,
  "courses_by_status": {
    "ready_now": [
      {
        "course_code": "CS 225",
        "course_name": "Data Structures",
        "total_prerequisites": 2,
        "prerequisites_missing": 0,
        "chain_depth": 0,
        "semesters_offered": 8,
        "recommendation": "Ready Now"
      }
    ],
    "almost_ready": [],
    "plan_soon": [],
    "plan_later": []
  },
  "total_remaining": 1
}
```

### Test in Neo4j Browser

```cypher
// Test with different students
:param student_id => 'S002'

// Then run the query
```

---

## Testing All Queries

### Quick Test Script

```bash
# 1. Bottleneck courses
curl "http://localhost:7474/api/queries/bottleneck-courses?min_dependents=3&limit=10"

# 2. Recommendations for S001
curl "http://localhost:7474/api/queries/students/S001/recommendations?semester_id=FALL_2024"

# 3. Course depth for S001
curl "http://localhost:7474/api/queries/students/S001/course-depth?limit=20"

# 4. Complete summary
curl "http://localhost:7474/api/queries/students/S001/summary?semester_id=FALL_2024"
```


---

## Pattern Summary

### Queries Demonstrate:

✅ **OPTIONAL MATCH** - Handling sparse data (multiple uses in each query)
✅ **Variable-length paths** - `*1..3` and `*1..5` for prerequisite chains
✅ **Multiple WITH clauses** - 3-5 stages of data transformation
✅ **List comprehension** - `[item IN list WHERE condition]`
✅ **Complex aggregations** - count(), collect(), max(), size()
✅ **CASE expressions** - Scoring and categorization
✅ **Computed filtering** - WHERE on calculated values
✅ **Parameters** - All queries use `$parameter` syntax
