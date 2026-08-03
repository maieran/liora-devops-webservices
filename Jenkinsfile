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
        stage('Prepare Environment') {
            steps {
                withCredentials([
                    file(credentialsId: 'liora-env-file', variable: 'ENV_FILE')
                ]) {
                    sh '''
                        rm -f .env.ci

                        install -m 600 "$ENV_FILE" .env.ci

                        CURRENT_IP="$(curl -fsS https://checkip.amazonaws.com | tr -d '\\n')"

                        sed -i '/^SERVER_HOST=/d' .env.ci
                        echo "SERVER_HOST=${CURRENT_IP}:8080" >> .env.ci

                        echo "Environment prepared for the current VM."
                        grep '^SERVER_HOST=' .env.ci
                    '''
                }
            }
        }

        stage('Build Docker Images') {
            steps {
                echo 'Building WordPress, PrestaShop and NGINX Docker images...'

                sh '''
                    docker compose --env-file .env.ci build
                    docker compose --env-file .env.ci config --images
                '''
            }
        }

        stage('Run Tests') {
            steps {
                echo 'Running project tests...'

                sh '''
                    chmod +x tests/run-tests.sh
                    chmod +x tests/health/health-check.sh
                    chmod +x tests/smoke/smoke-test.sh

                    SERVER_HOST="$(grep '^SERVER_HOST=' .env.ci | cut -d= -f2-)"

                    if [ -z "$SERVER_HOST" ]; then
                        echo "ERROR: SERVER_HOST is empty in .env.ci"
                        exit 1
                    fi

                    echo "Testing against: http://${SERVER_HOST}"

                    BASE_URL="http://${SERVER_HOST}" ./tests/run-tests.sh
                '''
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
                    docker compose --env-file .env.ci push
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
                sh '''
                    docker compose --env-file .env.ci config --images

                    docker compose --env-file .env.ci \
                        pull nginx wordpress prestashop

                    docker compose --env-file .env.ci up -d \
                        --no-build \
                        --remove-orphans \
                        --wait \
                        --wait-timeout 180

                    docker compose --env-file .env.ci ps
                '''
            }
        }

    }
}