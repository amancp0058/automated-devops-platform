import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT / "requirements.txt"
OUTPUT_DIR = ROOT / "generated"

ALLOWED_KEYS = {
    "APP_TYPE", "APP_PORT", "START_COMMAND",
    "MYSQL", "MYSQL_VERSION", "MYSQL_PORT",
    "REDIS", "REDIS_PORT", "CPU", "MEMORY"
}


def parse_requirements():
    packages = []
    config = {}

    with open(INPUT_FILE, "r") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=(?!=)", line):
                key, value = line.split("=", 1)
                key = key.strip().upper()
                value = value.strip()

                if key not in ALLOWED_KEYS:
                    raise ValueError(f"Unknown configuration key at line {line_number}: {key}")

                if key in config:
                    raise ValueError(f"Duplicate configuration key: {key}")

                config[key] = value
            else:
                if line.startswith("-"):
                    raise ValueError(f"Unsupported pip option at line {line_number}")

                packages.append(line)

    return packages, config


def validate_config(config):
    required = [
        "APP_TYPE", "APP_PORT", "START_COMMAND",
        "MYSQL", "REDIS", "CPU", "MEMORY"
    ]

    for key in required:
        if key not in config:
            raise ValueError(f"Missing required configuration: {key}")

    if config["APP_TYPE"] != "python":
        raise ValueError("Only Python applications are currently supported")

    if not config["START_COMMAND"]:
        raise ValueError("START_COMMAND cannot be empty")

    for key in ["MYSQL", "REDIS"]:
        if config[key].lower() not in ["true", "false"]:
            raise ValueError(f"{key} must be true or false")

    for key in ["APP_PORT", "MYSQL_PORT", "REDIS_PORT"]:
        if key in config:
            try:
                port = int(config[key])
            except ValueError:
                raise ValueError(f"{key} must be a number")

            if not 1 <= port <= 65535:
                raise ValueError(f"Invalid port: {key}")

    try:
        cpu = int(config["CPU"])
    except ValueError:
        raise ValueError("CPU must be a positive integer")

    if cpu <= 0:
        raise ValueError("CPU must be greater than zero")

    if not re.fullmatch(r"\d+(MB|GB)", config["MEMORY"], re.IGNORECASE):
        raise ValueError("MEMORY must look like 512MB or 2GB")

    if config["MYSQL"].lower() == "true":
        if "MYSQL_VERSION" not in config or "MYSQL_PORT" not in config:
            raise ValueError("MYSQL_VERSION and MYSQL_PORT are required when MYSQL=true")

    if config["REDIS"].lower() == "true":
        if "REDIS_PORT" not in config:
            raise ValueError("REDIS_PORT is required when REDIS=true")


def yaml_string(value):
    return json.dumps(str(value))


def generate_files(packages, config):
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Generate Python requirements
    pip_file = OUTPUT_DIR / "pip-requirements.txt"

    with open(pip_file, "w") as file:
        file.write("\n".join(packages) + "\n")

    # Generate infrastructure.yaml
    yaml_file = OUTPUT_DIR / "infrastructure.yaml"

    lines = [
        "application:",
        f"  type: {yaml_string(config['APP_TYPE'])}",
        f"  port: {int(config['APP_PORT'])}",
        f"  start_command: {yaml_string(config['START_COMMAND'])}",
        "",
        "dependencies:",
        "  file: generated/pip-requirements.txt",
        "",
        "servers:",
        "  mysql:",
        f"    enabled: {config['MYSQL'].lower()}"
    ]

    if config["MYSQL"].lower() == "true":
        lines.extend([
            f"    version: {yaml_string(config['MYSQL_VERSION'])}",
            f"    port: {int(config['MYSQL_PORT'])}"
        ])

    lines.extend([
        "  redis:",
        f"    enabled: {config['REDIS'].lower()}"
    ])

    if config["REDIS"].lower() == "true":
        lines.append(f"    port: {int(config['REDIS_PORT'])}")

    lines.extend([
        "",
        "resources:",
        f"  cpu: {int(config['CPU'])}",
        f"  memory: {yaml_string(config['MEMORY'])}"
    ])

    with open(yaml_file, "w") as file:
        file.write("\n".join(lines) + "\n")

    # Generate Dockerfile
    dockerfile_path = OUTPUT_DIR / "Dockerfile"

    dockerfile_content = f"""
FROM python:3.12-slim

WORKDIR /app

COPY generated/pip-requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY application/ /app/

EXPOSE {int(config['APP_PORT'])}

CMD ["sh", "-c", {json.dumps(config['START_COMMAND'])}]
"""

    with open(dockerfile_path, "w") as file:
        file.write(dockerfile_content.strip() + "\n")

    # Generate compose.yaml
    compose_file = OUTPUT_DIR / "compose.yaml"

    memory = (
        config["MEMORY"].upper()
        .replace("MB", "M")
        .replace("GB", "G")
    )

    compose_lines = [
        "services:",
        "  app:",
        "    build:",
        "      context: ..",
        "      dockerfile: generated/Dockerfile",
        "    image: automated-devops-app:latest",
        "    ports:",
        f"      - {yaml_string(str(config['APP_PORT']) + ':' + str(config['APP_PORT']))}",
        "    restart: unless-stopped",
        "    deploy:",
        "      resources:",
        "        limits:",
        f"          cpus: {yaml_string(str(config['CPU']))}",
        f"          memory: {yaml_string(memory)}"
    ]

    if config["MYSQL"].lower() == "true":
        compose_lines.extend([
            "",
            "  mysql:",
            f"    image: mysql:{config['MYSQL_VERSION']}",
            "    environment:",
            "      MYSQL_ROOT_PASSWORD: ${{MYSQL_ROOT_PASSWORD:?Set MYSQL_ROOT_PASSWORD}}",
            "      MYSQL_DATABASE: appdb",
            "    ports:",
            f"      - {yaml_string(str(config['MYSQL_PORT']) + ':3306')}",
            "    volumes:",
            "      - mysql_data:/var/lib/mysql",
            "    restart: unless-stopped"
        ])

    if config["REDIS"].lower() == "true":
        compose_lines.extend([
            "",
            "  redis:",
            "    image: redis:7-alpine",
            "    ports:",
            f"      - {yaml_string(str(config['REDIS_PORT']) + ':6379')}",
            "    restart: unless-stopped"
        ])

    if config["MYSQL"].lower() == "true":
        compose_lines.extend([
            "",
            "volumes:",
            "  mysql_data:"
        ])

    with open(compose_file, "w") as file:
        file.write("\n".join(compose_lines) + "\n")

    print("\nGeneration successful!")
    print(f"Python dependencies: {pip_file}")
    print(f"Infrastructure definition: {yaml_file}")
    print(f"Dockerfile: {dockerfile_path}")
    print(f"Docker Compose: {compose_file}")


def main():
    try:
        packages, config = parse_requirements()
        validate_config(config)
        generate_files(packages, config)

    except (ValueError, OSError) as error:
        print(f"\nERROR: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
