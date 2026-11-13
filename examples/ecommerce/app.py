from flask import Flask, jsonify
import mysql.connector
import redis
import os
import json
import time

app = Flask(__name__)

# MySQL configuration
db_config = {
    "host": os.getenv("MYSQL_HOST", "mysql"),
    "user": os.getenv("MYSQL_USER", "ecommerce_user"),
    "password": os.getenv("MYSQL_PASSWORD", "ecommerce_password"),
    "database": os.getenv("MYSQL_DATABASE", "ecommerce")
}

# Redis configuration
cache = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=6379,
    decode_responses=True
)


def get_db():
    return mysql.connector.connect(**db_config)


def initialize_database():

    for attempt in range(30):

        try:
            connection = get_db()
            cursor = connection.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    price DECIMAL(10,2) NOT NULL
                )
            """)

            cursor.execute("""
                INSERT INTO products (name, price)
                SELECT 'Laptop', 55000
                WHERE NOT EXISTS (
                    SELECT 1 FROM products WHERE name = 'Laptop'
                )
            """)

            cursor.execute("""
                INSERT INTO products (name, price)
                SELECT 'Smartphone', 25000
                WHERE NOT EXISTS (
                    SELECT 1 FROM products WHERE name = 'Smartphone'
                )
            """)

            connection.commit()

            cursor.close()
            connection.close()

            print("MySQL database initialized")
            return

        except Exception as error:

            print(f"Waiting for MySQL: {error}")

            time.sleep(3)

    raise RuntimeError("MySQL connection failed")


@app.route("/")
def home():

    return """
    <h1>DevOps E-Commerce Application</h1>
    <p>Application deployed using automated DevOps infrastructure.</p>
    <a href="/products">View Products</a>
    """


@app.route("/products")
def products():

    try:

        cached = cache.get("products")

        if cached:

            return jsonify({
                "source": "Redis Cache",
                "products": json.loads(cached)
            })

        connection = get_db()

        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT * FROM products")

        results = cursor.fetchall()

        cursor.close()
        connection.close()

        for product in results:
            product["price"] = float(product["price"])

        cache.setex(
            "products",
            60,
            json.dumps(results)
        )

        return jsonify({
            "source": "MySQL Database",
            "products": results
        })

    except Exception as error:

        return jsonify({"error": str(error)}), 500


@app.route("/health")
def health():

    try:

        connection = get_db()
        connection.close()

        cache.ping()

        return jsonify({
            "status": "healthy",
            "mysql": "connected",
            "redis": "connected"
        })

    except Exception as error:

        return jsonify({
            "status": "unhealthy",
            "error": str(error)
        }), 503


if __name__ == "__main__":

    initialize_database()

    app.run(
        host="0.0.0.0",
        port=5000
    )

