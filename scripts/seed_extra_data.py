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

    driver.close()
    print("✔ Extra data imported successfully.\n")


if __name__ == "__main__":
    main()
