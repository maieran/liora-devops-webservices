pipeline {
    agent any

    stages {

        stage('Pipeline Check') {
            steps {
                echo 'Liora CI/CD pipeline is running successfully.'
            }
        }

        stage('Environment Info') {
            steps {
                sh 'pwd'
                sh 'ls -la'
                sh 'docker --version'
                sh 'docker compose version'
            }
        }

        stage('Build Docker Images') {
            steps {
                echo 'Building WordPress, PrestaShop and NGINX Docker images...'
                sh 'docker compose build'
            }
        }

        stage('Run Tests') {
            steps {
                echo 'Running project tests...'
                sh 'chmod +x tests/run-tests.sh'
                sh './tests/run-tests.sh'
            }
        }

    }
}