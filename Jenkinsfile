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

    }
}