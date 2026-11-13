import json
import argparse
from pathlib import Path


class InfrastructureBuilder:

    def __init__(self, project_path):

        self.project = Path(project_path).resolve()

        self.generated = self.project / "generated"

        self.config_file = self.generated / "infrastructure.json"

        self.config = {}

    def load_configuration(self):

        if not self.config_file.exists():
            raise FileNotFoundError(
                "infrastructure.json not found. Run the analyzer first."
            )

        with open(self.config_file) as file:
            self.config = json.load(file)

        print("Infrastructure configuration loaded.")

    def generate_dockerfile(self):

        dockerfile = """
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
"""

        (self.generated / "Dockerfile").write_text(
            dockerfile.strip() + "\n"
        )

        print("Dockerfile generated.")

    def generate_nginx(self):

        port = self.config["application"]["port"]

        nginx = f"""
server {{

    listen 80;

    location / {{

        proxy_pass http://app:{port};

        proxy_set_header Host $host;

        proxy_set_header X-Real-IP $remote_addr;

        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

    }}

}}
"""

        (self.generated / "nginx.conf").write_text(
            nginx.strip() + "\n"
        )

        print("Nginx configuration generated.")

    def generate_compose(self):

        services = self.config["services"]

        app_port = self.config["application"]["port"]

        compose = f"""
services:

  app:

    build:
      context: .
      dockerfile: generated/Dockerfile

    restart: unless-stopped

    environment:
      MYSQL_HOST: mysql
      MYSQL_USER: ${{MYSQL_USER:-ecommerce_user}}
      MYSQL_PASSWORD: ${{MYSQL_PASSWORD:-ecommerce_password}}
      MYSQL_DATABASE: ${{MYSQL_DATABASE:-ecommerce}}
      REDIS_HOST: redis

    depends_on:
"""

        if services.get("mysql"):
            compose += """
      mysql:
        condition: service_healthy
"""

        if services.get("redis"):
            compose += """
      redis:
        condition: service_healthy
"""

        compose += f"""
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - "import urllib.request; urllib.request.urlopen('http://127.0.0.1:{app_port}/health')"
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 30s
"""

        if services.get("mysql"):

            compose += """

  mysql:

    image: mysql:8.0

    restart: unless-stopped

    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-local_root_password}
      MYSQL_DATABASE: ${MYSQL_DATABASE:-ecommerce}
      MYSQL_USER: ${MYSQL_USER:-ecommerce_user}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-ecommerce_password}

    volumes:
      - mysql_data:/var/lib/mysql

    healthcheck:
      test:
        - CMD
        - mysqladmin
        - ping
        - -h
        - localhost
        - -uroot
        - -p${MYSQL_ROOT_PASSWORD:-local_root_password}
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
"""

        if services.get("redis"):

            compose += """

  redis:

    image: redis:7-alpine

    restart: unless-stopped

    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
"""

        compose += """

  nginx:

    image: nginx:alpine

    restart: unless-stopped

    ports:
      - "7000:80"

    volumes:
      - ./generated/nginx.conf:/etc/nginx/conf.d/default.conf:ro

    depends_on:
      app:
        condition: service_healthy

volumes:
"""

        if services.get("mysql"):
            compose += """
  mysql_data:
"""

        (self.generated / "compose.yaml").write_text(
            compose.strip() + "\n"
        )

        print("Docker Compose configuration generated.")

    def run(self):

        print("\n================================")
        print(" INFRASTRUCTURE BUILDER")
        print("================================\n")

        print("Project:", self.project)

        self.generated.mkdir(
            parents=True,
            exist_ok=True
        )

        self.load_configuration()

        self.generate_dockerfile()

        self.generate_nginx()

        self.generate_compose()

        print("\nInfrastructure generation completed!")

        print("\nGenerated files:")

        for file in self.generated.iterdir():

            if file.is_file():
                print(" -", file.name)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "project",
        help="Application project directory"
    )

    args = parser.parse_args()

    builder = InfrastructureBuilder(args.project)

    builder.run()


if __name__ == "__main__":
    main()
