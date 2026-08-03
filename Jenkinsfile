pipeline {
    agent any

     environment {
        DOCKERHUB_USERNAME = 'shabbyalaei'
        IMAGE_TAG = "${BUILD_NUMBER}"
    }

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
                sh 'echo "Git branch: $GIT_BRANCH"'
                sh 'echo "Build number: $BUILD_NUMBER"'
            }
        }

        stage('Build Docker Images') {
            steps {
                echo 'Building WordPress, PrestaShop and NGINX Docker images...'
                sh 'docker compose build'
                sh 'docker compose config --images'
            }
        }

        stage('Run Tests') {
            steps {
                echo 'Running project tests...'
                sh 'chmod +x tests/run-tests.sh'
                sh './tests/run-tests.sh'
            }
        }

        stage('Docker Login') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'liora-dockerhub-credentials',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_TOKEN'
                    )
                ]) {
                    sh '''
                        echo "$DOCKER_TOKEN" | docker login \
                        -u "$DOCKER_USER" \
                        --password-stdin
                    '''
                }
            }
        }

        stage('Push Docker Images') {
            steps {
                sh '''
                    docker compose push
                '''
            }
        }

        stage('Deploy Dev') {
              when {
                expression {
                    env.GIT_BRANCH == 'origin/feature/jenkins-cicd' ||
                    env.GIT_BRANCH == 'origin/main'
                }
            }
            steps {
                withCredentials([
                    file(credentialsId: 'liora-env-file', variable: 'ENV_FILE')
                ]) {

                    sh '''
                        cp "$ENV_FILE" .env
                    '''

                    sh '''
                        docker compose pull nginx wordpress prestashop

                        docker compose up -d \
                            --no-build \
                            --remove-orphans \
                            --wait \
                            --wait-timeout 180

                        docker compose ps
                    '''
                }
            }
        }

        

    }
}