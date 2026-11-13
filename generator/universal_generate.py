import ast
import argparse
import re
import json

from pathlib import Path


class UniversalAnalyzer:

    def __init__(self, project_path):

        self.project = Path(project_path).resolve()

        self.requirements_file = self.project / "requirements.txt"

        self.dependencies = set()
        self.imports = set()

        self.framework = None
        self.port = 5000

        self.services = {
            "mysql": False,
            "postgresql": False,
            "mongodb": False,
            "redis": False
        }

    # ----------------------------------
    # Read standard requirements.txt
    # ----------------------------------

    def analyze_requirements(self):

        if not self.requirements_file.exists():
            raise FileNotFoundError(
                "requirements.txt not found"
            )

        with open(self.requirements_file) as file:

            for line in file:

                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if line.startswith("-"):
                    continue

                match = re.match(
                    r"^([A-Za-z0-9_.-]+)",
                    line
                )

                if match:

                    package = match.group(1).lower()

                    self.dependencies.add(package)

        print("\nDetected Python dependencies:")

        for package in sorted(self.dependencies):
            print(f"  - {package}")

    # ----------------------------------
    # Analyze Python source code
    # ----------------------------------

    def analyze_source(self):

        python_files = list(
            self.project.rglob("*.py")
        )

        if not python_files:
            raise RuntimeError(
                "No Python source files found"
            )

        for file_path in python_files:

            if any(
                part in {
                    ".git",
                    ".venv",
                    "venv",
                    "__pycache__",
                    "generated"
                }
                for part in file_path.parts
            ):
                continue

            try:

                source = file_path.read_text()

                tree = ast.parse(source)

                for node in ast.walk(tree):

                    if isinstance(node, ast.Import):

                        for item in node.names:
                            self.imports.add(
                                item.name.split(".")[0]
                            )

                    elif isinstance(node, ast.ImportFrom):

                        if node.module:
                            self.imports.add(
                                node.module.split(".")[0]
                            )

                # Detect application server port using AST

                # Detect application server port using AST

                for node in ast.walk(tree):

                    if isinstance(node, ast.Call):

                        function_name = ""

                        if isinstance(node.func, ast.Attribute):
                            function_name = node.func.attr

                        elif isinstance(node.func, ast.Name):
                            function_name = node.func.id

                        if function_name == "run":

                            for keyword in node.keywords:

                                if (
                                    keyword.arg == "port"
                                    and isinstance(keyword.value, ast.Constant)
                                    and isinstance(keyword.value.value, int)
                                ):
                                    self.port = keyword.value.value
                # Detect service host configuration

                if re.search(
                    r"""(?:MYSQL_HOST|host)\s*.*?["']mysql["']""",
                    source,
                    re.IGNORECASE
                ):
                    self.services["mysql"] = True

                if re.search(
                    r"""(?:REDIS_HOST|host)\s*.*?["']redis["']""",
                    source,
                    re.IGNORECASE
                ):
                    self.services["redis"] = True

                if re.search(
                    r"""(?:POSTGRES_HOST|host)\s*.*?["']postgres["']""",
                    source,
                    re.IGNORECASE
                ):
                    self.services["postgresql"] = True

                if re.search(
                    r"""(?:MONGO_HOST|host)\s*.*?["']mongodb["']""",
                    source,
                    re.IGNORECASE
                ):
                    self.services["mongodb"] = True

            except SyntaxError as error:

                raise RuntimeError(
                    f"Invalid Python file: {file_path}: {error}"
                )

        print("\nDetected Python imports:")

        for item in sorted(self.imports):
            print(f"  - {item}")

    # ----------------------------------
    # Detect application framework
    # ----------------------------------

    def detect_framework(self):

        if "django" in self.dependencies or "django" in self.imports:

            self.framework = "django"

        elif "fastapi" in self.dependencies or "fastapi" in self.imports:

            self.framework = "fastapi"

        elif "flask" in self.dependencies or "flask" in self.imports:

            self.framework = "flask"

        else:

            self.framework = "python"

        print("\nDetected framework:", self.framework)

    # ----------------------------------
    # Detect infrastructure services
    # ----------------------------------

    def detect_services(self):

        if (
            "mysql-connector-python" in self.dependencies
            or "pymysql" in self.dependencies
            or "mysqlclient" in self.dependencies
            or "mysql" in self.imports
        ):
            print("MySQL client integration detected")

        if (
            "psycopg2" in self.dependencies
            or "psycopg2-binary" in self.dependencies
            or "psycopg" in self.imports
        ):
            print("PostgreSQL client integration detected")

        if (
            "pymongo" in self.dependencies
            or "pymongo" in self.imports
        ):
            print("MongoDB client integration detected")

        if (
            "redis" in self.dependencies
            or "redis" in self.imports
        ):
            print("Redis client integration detected")

        print("\nRequired local infrastructure:")

        for service, enabled in self.services.items():

            print(
                f"  {service}: "
                f"{'enabled' if enabled else 'not detected'}"
            )

    # ----------------------------------
    # Generate infrastructure definition
    # ----------------------------------

    def generate_infrastructure(self):

        output_dir = self.project / "generated"

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        infrastructure = {

            "application": {
                "framework": self.framework,
                "port": self.port
            },

            "dependencies": sorted(
                self.dependencies
            ),

            "services": self.services

        }

        output_file = (
            output_dir / "infrastructure.json"
        )

        with open(output_file, "w") as file:

            json.dump(
                infrastructure,
                file,
                indent=4
            )

        print("\nInfrastructure analysis generated!")

        print(output_file)

    # ----------------------------------
    # Run analyzer
    # ----------------------------------

    def run(self):

        print("\n================================")
        print(" UNIVERSAL APPLICATION ANALYZER")
        print("================================")

        print("\nProject:", self.project)

        self.analyze_requirements()

        self.analyze_source()

        self.detect_framework()

        self.detect_services()

        self.generate_infrastructure()

        print("\nAnalysis completed successfully!")


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "project",
        help="Application project directory"
    )

    args = parser.parse_args()

    analyzer = UniversalAnalyzer(
        args.project
    )

    analyzer.run()


if __name__ == "__main__":

    main()
