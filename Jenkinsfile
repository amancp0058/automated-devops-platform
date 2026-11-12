pipeline {
    agent any

    options {
        timestamps()
        skipDefaultCheckout(true)
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out latest source code'
                checkout scm
            }
        }

        stage('Generate Infrastructure') {
            steps {
                sh '''
                    python3 --version
                    python3 generator/generate.py
                '''
            }
        }

        stage('Validate Configuration') {
            steps {
                sh '''
                    docker compose -p generated -f generated/compose.yaml config --quiet
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    docker compose -p generated -f generated/compose.yaml build
                '''
            }
        }

        stage('Deploy Application') {
            steps {
                sh '''
                    docker compose -p generated -f generated/compose.yaml up -d
                '''
            }
        }

        stage('Health Check') {
            steps {
                sh '''
                    for attempt in $(seq 1 15)
                    do
                        if curl --fail --silent http://127.0.0.1:5000/health
                        then
                            echo "Application is healthy!"
                            exit 0
                        fi

                        echo "Waiting for application..."
                        sleep 2
                    done

                    docker compose -p generated -f generated/compose.yaml logs app
                    exit 1
                '''
            }
        }
    }

    post {
        success {
            echo 'Deployment completed successfully!'
        }

        failure {
            echo 'Pipeline failed. Check the Jenkins console output.'
        }
    }
}
