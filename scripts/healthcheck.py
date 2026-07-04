import os
import sys
import psycopg2
from neo4j import GraphDatabase
import redis

def check_postgres(host, port, user, password, dbname):
    print(f"Connecting to PostgreSQL at {host}:{port}...", end=" ")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            connect_timeout=3
        )
        conn.close()
        print("OK")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

def check_neo4j(uri, user, password):
    print(f"Connecting to Neo4j at {uri}...", end=" ")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        print("OK")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

def check_redis(url):
    print(f"Connecting to Redis at {url}...", end=" ")
    try:
        r = redis.from_url(url, socket_timeout=3)
        r.ping()
        print("OK")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

def main():
    pg_host = os.environ.get("POSTGRES_HOST", "localhost")
    pg_port = os.environ.get("POSTGRES_PORT", "55432")
    pg_user = os.environ.get("POSTGRES_USER", "postgres")
    pg_pass = os.environ.get("POSTGRES_PASSWORD", "postgres")
    pg_db = os.environ.get("POSTGRES_DB", "rakshanet")

    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_pass = os.environ.get("NEO4J_PASSWORD", "neo4jpassword")

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    print("--- RakshaNet Database Health Check ---")
    pg_ok = check_postgres(pg_host, pg_port, pg_user, pg_pass, pg_db)
    neo_ok = check_neo4j(neo4j_uri, neo4j_user, neo4j_pass)
    redis_ok = check_redis(redis_url)

    if pg_ok and neo_ok and redis_ok:
        print("\nAll database services are HEALTHY.")
        sys.exit(0)
    else:
        print("\nOne or more database services are UNHEALTHY.")
        sys.exit(1)

if __name__ == "__main__":
    main()
