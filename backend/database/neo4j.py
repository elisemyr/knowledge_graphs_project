"""
Database module for managing the Neo4j driver.

This module exposes a Neo4jClient class and a get_neo4j_client factory
used by the rest of the application to run Cypher queries.
"""

from __future__ import annotations
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import Neo4jError


class Neo4jClient:
    """
    Lightweight wrapper around the Neo4j driver.

    Usage:
        client = get_neo4j_client()
        records = client.query("MATCH (n) RETURN n LIMIT 5")
    """

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: Optional[str] = None,
    ) -> None:
        """
        Initialize the Neo4j driver.

        Args:
            uri: Bolt URI of the Neo4j instance.
            user: Username for authentication.
            password: Password for authentication.
            database: Optional database name (Neo4j 4+).
        """
        self._uri: str = uri
        self._user: str = user
        self._password: str = password
        self._database: Optional[str] = database

        self._driver: Driver = GraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password),
        )

    def close(self) -> None:
        """Close the underlying driver."""
        if self._driver is not None:
            self._driver.close()

    def session(self, **kwargs) -> Session:
        """
        Create a new session.

        Args:
            **kwargs: Optional keyword arguments passed to driver.session().

        Returns:
            A Neo4j session bound to the configured database (if any).
        """
        if self._database:
            return self._driver.session(database=self._database, **kwargs)
        return self._driver.session(**kwargs)

    def _get_session(self) -> Session:
        """
        Create a new session.

        Returns:
            A Neo4j session bound to the configured database (if any).
        """
        if self._database:
            return self._driver.session(database=self._database)
        return self._driver.session()

    def query(
        self,
        cypher: str,
        parameters: Optional[Dict[str, Any]] = None,
        read_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return the results as a list of dicts.

        Args:
            cypher: The Cypher query string.
            parameters: Optional dictionary of query parameters.
            read_only: If True, run in a read transaction.

        Returns:
            List of records as dictionaries.

        Raises:
            Neo4jError: If the query execution fails.
        """
        parameters = parameters or {}

        try:
            with self._get_session() as session:
                if read_only:
                    result = session.execute_read(lambda tx: list(tx.run(cypher, **parameters)))
                else:
                    result = session.execute_write(lambda tx: list(tx.run(cypher, **parameters)))

            # Convert records to plain dicts
            return [record.data() for record in result]

        except Neo4jError as exc:
            # You can improve logging later
            raise RuntimeError(f"Neo4j query failed: {exc}") from exc


@lru_cache(maxsize=1)
def get_neo4j_client() -> Neo4jClient:
    """
    Factory for a singleton Neo4jClient.

    Values are read from environment variables:
        NEO4J_URI
        NEO4J_USER
        NEO4J_PASSWORD
        NEO4J_DATABASE

    Returns:
        A cached Neo4jClient instance.
    """
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    return Neo4jClient(uri=uri, user=user, password=password, database=database)


@lru_cache(maxsize=1)
def get_neo4j_driver() -> Driver:
    """
    Factory for a singleton Neo4j Driver.

    This function provides direct access to the Neo4j driver for services
    that need to use sessions directly (e.g., for GDS operations).

    Values are read from environment variables:
        NEO4J_URI
        NEO4J_USER
        NEO4J_PASSWORD

    Returns:
        A cached Neo4j Driver instance.
    """
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    return GraphDatabase.driver(uri, auth=(user, password))
