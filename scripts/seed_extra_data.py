"""
Supplemental seed script for importing:
- Degrees
- Degree requirements
- Students
- Student course enrollments

This script DOES NOT MODIFY the existing seed_data.py,
and uses the same Neo4j driver logic.
"""

from __future__ import annotations
import csv
import os
from pathlib import Path
from neo4j import GraphDatabase


# --------------------------------------------------------------
# REUSE SAME CONNECTION SETUP AS seed_data.py
# --------------------------------------------------------------

def get_driver():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    return GraphDatabase.driver(uri, auth=(user, password))


def run_write(driver, cypher: str, params: dict = None):
    params = params or {}
    db = os.getenv("NEO4J_DATABASE", "neo4j")
    with driver.session(database=db) as session:
        session.execute_write(lambda tx: tx.run(cypher, **params))


# --------------------------------------------------------------
# IMPORT FUNCTIONS
# --------------------------------------------------------------

def import_degrees(driver, csv_path: Path):
    print(f"Importing degrees from: {csv_path}")
    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            run_write(
                driver,
                """
                MERGE (d:Degree {id: $id})
                SET d.degree_id = $id,
                    d.name = $name,
                    d.subject_prefix = $prefix,
                    d.description = $desc
                """,
                {
                    "id": row["degree_id"],
                    "name": row["degree_name"],
                    "prefix": row["subject_prefix"],
                    "desc": row["description"],
                }
            )
    print("✔ Degrees imported.\n")


def import_degree_requirements(driver, csv_path: Path):
    print(f"Importing degree requirements from: {csv_path}")
    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            run_write(
                driver,
                """
                MATCH (d:Degree {id: $degree})
                MERGE (c:Course {code: $course})
                MERGE (c)-[:REQUIRED_FOR]->(d)
                """,
                {"degree": row["degree_id"], "course": row["course"]}
            )
    print("✔ Degree requirements imported.\n")


def import_students(driver, csv_path: Path):
    print(f"Importing students from: {csv_path}")
    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            run_write(
                driver,
                """
                MERGE (s:Student {student_id: $sid})
                SET s.name = $name,
                    s.year = $year,
                    s.profile = $profile
                """,
                {
                    "sid": row["student_id"],
                    "name": row["name"],
                    "year": row["year"],
                    "profile": row["profile"],
                }
            )

            # Enroll student in degree
            run_write(
                driver,
                """
                MATCH (s:Student {student_id: $sid})
                MATCH (d:Degree {id: $degree})
                MERGE (s)-[:ENROLLED_IN]->(d)
                """,
                {"sid": row["student_id"], "degree": row["degree_id"]}
            )
    print("✔ Students imported.\n")


def import_student_enrollments(driver, csv_path: Path):
    print(f"Importing student enrollments from: {csv_path}")
    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            run_write(
                driver,
                """
                MATCH (s:Student {student_id: $sid})
                MERGE (c:Course {code: $course})
                MERGE (s)-[:HAS_COMPLETED]->(c)
                """,
                {"sid": row["student_id"], "course": row["course"]}
            )
    print("✔ Enrollments imported.\n")

def create_semesters_and_offerings(driver):
    """
    Create Semester nodes and OFFERED_IN relationships
    """
    print("Creating semesters...")
    
    # Define semesters (4 years worth)
    semesters = []
    current_year = 2024
    for year_offset in range(4):  # 4 years
        year = current_year + year_offset
        semesters.extend([
            {
                "id": f"FALL_{year}",
                "name": f"Fall {year}",
                "year": year,
                "term": "Fall",
                "order": year_offset * 2  # For ordering: 0, 2, 4, 6...
            },
            {
                "id": f"SPRING_{year + 1}",
                "name": f"Spring {year + 1}",
                "year": year + 1,
                "term": "Spring",
                "order": year_offset * 2 + 1  # For ordering: 1, 3, 5, 7...
            }
        ])
    
    # Create Semester nodes
    with driver.session() as session:
        # Create constraint on semester ID
        try:
            session.run("""
                CREATE CONSTRAINT semester_id_unique IF NOT EXISTS
                FOR (s:Semester) REQUIRE s.id IS UNIQUE
            """)
        except Exception as e:
            print(f"Constraint may already exist: {e}")
        
        # Create semester nodes
        session.run("""
            UNWIND $semesters AS semester
            MERGE (s:Semester {id: semester.id})
            SET s.name = semester.name,
                s.year = semester.year,
                s.term = semester.term,
                s.order = semester.order
        """, semesters=semesters)
        
        print(f"Created {len(semesters)} semester nodes")
        
        # Create OFFERED_IN relationships
        # Strategy: Most courses offered every semester, some only Fall or Spring
        print("Creating OFFERED_IN relationships...")
        
        # Get all courses
        result = session.run("MATCH (c:Course) RETURN c.code as code")
        courses = [record["code"] for record in result]
        
        offerings_created = 0
        
        for course_code in courses:
            # Simple heuristic: 
            # - Intro courses (100-level): offered every semester
            # - Mid-level (200-300): offered every semester
            # - Advanced (400+): maybe only Fall or only Spring
            
            # Extract course level from code (e.g., "CS 101" -> 101)
            try:
                parts = course_code.split()
                if len(parts) >= 2:
                    course_num = int(''.join(filter(str.isdigit, parts[1])))
                else:
                    course_num = 0
            except:
                course_num = 0
            
            # Determine which semesters to offer the course
            if course_num < 400:
                # Offer every semester
                offered_semesters = [s["id"] for s in semesters]
            else:
                # Advanced courses: alternate or limit offerings
                # For simplicity, offer only in Fall semesters
                offered_semesters = [s["id"] for s in semesters if s["term"] == "Fall"]
            
            # Create relationships
            for semester_id in offered_semesters:
                session.run("""
                    MATCH (c:Course {code: $course_code})
                    MATCH (s:Semester {id: $semester_id})
                    MERGE (c)-[:OFFERED_IN]->(s)
                """, course_code=course_code, semester_id=semester_id)
                offerings_created += 1
        
        print(f"Created {offerings_created} OFFERED_IN relationships")
        
        # Create some sample students with completed courses
        print("Creating sample students...")
        sample_students = [
            {
                "id": "S001",
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "program": "Computer Science",
                "completed": ["CS 101", "MATH 220", "PHYS 211"]
            },
            {
                "id": "S002", 
                "name": "Bob Smith",
                "email": "bob@example.com",
                "program": "Computer Science",
                "completed": ["CS 101", "CS 173", "MATH 220", "MATH 231"]
            },
            {
                "id": "S003",
                "name": "Carol Williams",
                "email": "carol@example.com", 
                "program": "Computer Science",
                "completed": []  # Freshman, no courses yet
            }
        ]
        
        for student in sample_students:
            # Create student node
            session.run("""
                MERGE (s:Student {id: $id})
                SET s.name = $name,
                    s.email = $email,
                    s.program = $program
            """, id=student["id"], name=student["name"], 
                 email=student["email"], program=student["program"])
            
            # Create HAS_COMPLETED relationships
            for course_code in student["completed"]:
                session.run("""
                    MATCH (s:Student {id: $student_id})
                    MATCH (c:Course {code: $course_code})
                    MERGE (s)-[:HAS_COMPLETED]->(c)
                """, student_id=student["id"], course_code=course_code)
        
        print(f"Created {len(sample_students)} sample students")


# --------------------------------------------------------------
# MAIN ENTRYPOINT
# --------------------------------------------------------------

def main():
    driver = get_driver()
    driver.verify_connectivity()
    print("\nConnected to Neo4j.\n")

    base = Path("data")

    import_degrees(driver, base / "degrees.csv")
    import_degree_requirements(driver, base / "degree_requirements.csv")
    import_students(driver, base / "students.csv")

    enrollments_csv = base / "student_enrollments.csv"
    if enrollments_csv.exists():
        import_student_enrollments(driver, enrollments_csv)
    else:
        print("⚠ No student_enrollments.csv file found. Skipping enrollment import.\n")

    create_semesters_and_offerings(driver)
    print("\nDatabase seeding complete with semesters.")

    driver.close()
    print("✔ Extra data imported successfully.\n")


if __name__ == "__main__":
    main()
