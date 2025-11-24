"""
Seed script for importing course prerequisites into Neo4j.

- Connects to Neo4j using environment variables
- Creates constraints and indexes for Course nodes
- Reads a wide CSV file of the form:

    Course,PrerequisiteNumber,0,1,2,3,4,5,6,7,8,9
    AAS 100,0
    AAS 105,0
    AAS 211,2,AAS 100,AAS 120
    ...

- Creates:
    (:Course {code}) nodes
    (:Course {code: prereq})-[:PRE_REQUIRES]->(:Course {code: course}) relationships
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import List

from neo4j import GraphDatabase, Driver



# neo4j connection utilities


def get_driver() -> Driver:
    """
    Create a Neo4j driver from environment variables.
    
    This connects to your Neo4j database. The driver is like a connection manager.
    
    Env vars (with defaults for local dev):
        NEO4J_URI       (default: bolt://localhost:7687)
        NEO4J_USER      (default: neo4j)
        NEO4J_PASSWORD  (default: password)
        NEO4J_DATABASE  (optional, default: neo4j)
    """
    # get connection info from environment, or use safe defaults
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    # create the driver 
    driver = GraphDatabase.driver(uri, auth=(user, password))
    return driver


def run_query(driver: Driver, cypher: str, parameters: dict | None = None) -> None:
    """
    Helper to run a write query with basic error handling.
    
    This is simpler for learning - we catch any Exception that might occur.
    """
    parameters = parameters or {}
    try:
        database_name = os.getenv("NEO4J_DATABASE", "neo4j")
        with driver.session(database=database_name) as session:
            # execute_write runs the query in a write transaction
            session.execute_write(lambda tx: tx.run(cypher, **parameters))
    except Exception as exc:
        # Convert any error to a more helpful message
        raise RuntimeError(f"Neo4j query failed: {exc}") from exc


# schema: constraints & indexes


def create_constraints_and_indexes(driver: Driver) -> None:
    """
    Create constraints and indexes for Course nodes.

    You can expand this later with more labels/indexes if needed.
    """
    print("🔧 Creating constraints and indexes (IF NOT EXISTS)...")

    queries = [
        # unique constraint on Course.code
        """
        CREATE CONSTRAINT course_code_unique IF NOT EXISTS
        FOR (c:Course)
        REQUIRE c.code IS UNIQUE
        """,
        # index on Course.name
        """
        CREATE INDEX course_name_index IF NOT EXISTS
        FOR (c:Course)
        ON (c.name)
        """,
    ]

    for cypher in queries:
        run_query(driver, cypher)

    print("✅ Constraints and indexes created.\n")



# CSV parsing & data import



def parse_prereqs_row(row: dict) -> List[str]:
    """
    Given a dict row from csv.DictReader with columns:
        Course, PrerequisiteNumber, 0,1,2,...,9

    Return the list of prerequisite course codes (non-empty, stripped).
    """
    # how many prerequisites are declared
    count_raw = (row.get("PrerequisiteNumber") or "").strip()
    try:
        prereq_count = int(count_raw) if count_raw else 0
    except ValueError:
        prereq_count = 0

    prereqs: List[str] = []

    # Columns 
    for i in range(prereq_count):
        col_name = str(i)
        code = (row.get(col_name) or "").strip()
        if code:
            prereqs.append(code)

    # deduplicate while preserving order
    seen = set()
    unique_prereqs: List[str] = []
    for code in prereqs:
        if code not in seen:
            seen.add(code)
            unique_prereqs.append(code)

    return unique_prereqs


def import_courses_from_csv(driver: Driver, csv_path: Path) -> None:
    """
    Read the CSV file and create Course nodes and PRE_REQUIRES relationships.

    For each row:
        - MERGE (:Course {code: course_code})
        - for each prereq_code:
            MERGE (:Course {code: prereq_code})
            MERGE (prereq)-[:PRE_REQUIRES]->(course)
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    print(f"Loading CSV: {csv_path}")

    created_courses = 0
    created_rel = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        # safety check on header
        expected_prefix = ["Course", "PrerequisiteNumber"]
        header = reader.fieldnames or []
        if not all(col in header for col in expected_prefix):
            raise ValueError(
                f"CSV header does not contain required columns {expected_prefix}. "
                f"Found: {header}"
            )

        for row in reader:
            course_code = (row.get("Course") or "").strip()
            if not course_code:
                continue

            # create and merge the course node itself
            run_query(
                driver,
                """
                MERGE (c:Course {code: $code})
                ON CREATE SET c.name = $code
                """,
                {"code": course_code},
            )
            created_courses += 1

            prereq_codes = parse_prereqs_row(row)
            if not prereq_codes:
                continue

            for prereq_code in prereq_codes:
                # merge ensures the prerequisite course exists and creates if it doesn't exist
                run_query(
                    driver,
                    """
                    MERGE (p:Course {code: $pr_code})
                    ON CREATE SET p.name = $pr_code
                    """,
                    {"pr_code": prereq_code},
                )

                # create the relationship: prerequisite -[:PRE_REQUIRES]-> course
                # merge ensures we don't create duplicate relationships
                run_query(
                    driver,
                    """
                    MATCH (p:Course {code: $pr_code})
                    MATCH (c:Course {code: $course_code})
                    MERGE (p)-[:PRE_REQUIRES]->(c)
                    """,
                    {"pr_code": prereq_code, "course_code": course_code},
                )
                created_rel += 1

    print(f"Import finished")
    print(f"   Courses processed: {created_courses}")
    print(f"   PRE_REQUIRES relationships created: {created_rel}\n")



# main entrypoint

def main() -> None:
    """
    Usage:
        python scripts/seed_data.py [path_to_csv]

    Example:
        python scripts/seed_data.py data/courses_prereq.csv
    """
    # default csv location
    default_path = Path("data") / "courses_prereq.csv"
    csv_arg = sys.argv[1] if len(sys.argv) > 1 else str(default_path)
    csv_path = Path(csv_arg)

    print(" Starting Neo4j seed script...")

    driver = get_driver()
    try:
        #check connectivity early
        driver.verify_connectivity()
        print(" connected to Neo4j successfully.\n")

        create_constraints_and_indexes(driver)
        import_courses_from_csv(driver, csv_path)

    finally:
        driver.close()
        print(" Neo4j driver closed.")


if __name__ == "__main__":
    main()
