pipeline {
    agent any

    environment {
        DOCKERHUB_USERNAME = 'shabbyalaei'
        IMAGE_TAG = "${BUILD_NUMBER}"

        DEV_PROJECT = 'liora-dev'
        STAGING_PROJECT = 'liora-staging'
        PROD_PROJECT = 'liora-prod'
    }

    options {
        disableConcurrentBuilds()
        timestamps()
    }

    stages {

        stage('Pipeline Check') {
            steps {
                echo 'Liora CI/CD pipeline is running successfully.'
                echo "Build number: ${BUILD_NUMBER}"
                echo "Image tag: ${IMAGE_TAG}"
            }
        }

        stage('Environment Info') {
            steps {
                sh '''
                    set -eu

                    echo "Workspace: $(pwd)"
                    echo "Git branch: ${GIT_BRANCH:-unknown}"
                    echo "Build number: ${BUILD_NUMBER}"

                    docker --version
                    docker compose version
                '''
            }
        }

        stage('Prepare Environments') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'liora-dev-env',
                        variable: 'DEV_ENV_FILE'
                    ),
                    file(
                        credentialsId: 'liora-staging-env',
                        variable: 'STAGING_ENV_FILE'
                    ),
                    file(
                        credentialsId: 'liora-prod-env',
                        variable: 'PROD_ENV_FILE'
                    )
                ]) {
                    sh '''
                        set -eu

                        rm -f .env.dev.ci .env.staging.ci .env.prod.ci

                        install -m 600 "$DEV_ENV_FILE" .env.dev.ci
                        install -m 600 "$STAGING_ENV_FILE" .env.staging.ci
                        install -m 600 "$PROD_ENV_FILE" .env.prod.ci

                        CURRENT_IP="$(curl -fsS https://checkip.amazonaws.com | tr -d '\\n')"

                        if [ -z "$CURRENT_IP" ]; then
                            echo "ERROR: Could not detect the current public IP."
                            exit 1
                        fi

                        # Development environment
                        sed -i '/^SERVER_HOST=/d' .env.dev.ci
                        sed -i '/^APP_PORT=/d' .env.dev.ci
                        echo "APP_PORT=8080" >> .env.dev.ci
                        echo "SERVER_HOST=${CURRENT_IP}:8080" >> .env.dev.ci

                        # Staging environment
                        sed -i '/^SERVER_HOST=/d' .env.staging.ci
                        sed -i '/^APP_PORT=/d' .env.staging.ci
                        echo "APP_PORT=8081" >> .env.staging.ci
                        echo "SERVER_HOST=${CURRENT_IP}:8081" >> .env.staging.ci

                        # Production environment
                        sed -i '/^SERVER_HOST=/d' .env.prod.ci
                        sed -i '/^APP_PORT=/d' .env.prod.ci
                        echo "APP_PORT=8082" >> .env.prod.ci
                        echo "SERVER_HOST=${CURRENT_IP}:8082" >> .env.prod.ci

                        echo "Environment files prepared successfully."
                        echo "Dev URL: http://${CURRENT_IP}:8080"
                        echo "Staging URL: http://${CURRENT_IP}:8081"
                        echo "Production URL: http://${CURRENT_IP}:8082"
                    '''
                }
            }
        }

        stage('Validate Compose Files') {
            steps {
                sh '''
                    set -eu

                    docker compose \
                        -p "$DEV_PROJECT" \
                        --env-file .env.dev.ci \
                        -f docker-compose.yml \
                        -f docker-compose.dev.yml \
                        config --quiet

                    docker compose \
                        -p "$STAGING_PROJECT" \
                        --env-file .env.staging.ci \
                        -f docker-compose.yml \
                        -f docker-compose.staging.yml \
                        config --quiet

                    docker compose \
                        -p "$PROD_PROJECT" \
                        --env-file .env.prod.ci \
                        -f docker-compose.yml \
                        -f docker-compose.prod.yml \
                        config --quiet

                    echo "All Docker Compose configurations are valid."
                '''
            }
        }

        stage('Build Docker Images') {
            steps {
                echo 'Building WordPress, PrestaShop and NGINX Docker images...'

                sh '''
                    set -eu

                    docker compose \
                        -p "$DEV_PROJECT" \
                        --env-file .env.dev.ci \
                        -f docker-compose.yml \
                        -f docker-compose.dev.yml \
                        build

                    echo "Built images:"

                    docker compose \
                        -p "$DEV_PROJECT" \
                        --env-file .env.dev.ci \
                        -f docker-compose.yml \
                        -f docker-compose.dev.yml \
                        config --images
                '''
            }
        }

        stage('Deploy Dev') {
            when {
                expression {
                    env.GIT_BRANCH == 'origin/feature/jenkins-cicd' ||
                    env.GIT_BRANCH == 'feature/jenkins-cicd' ||
                    env.GIT_BRANCH == 'origin/main' ||
                    env.GIT_BRANCH == 'main'
                }
            }

            steps {
                echo "Deploying development environment with image tag ${IMAGE_TAG}..."

                sh '''
                    set -eu

                    docker compose \
                        -p "$DEV_PROJECT" \
                        --env-file .env.dev.ci \
                        -f docker-compose.yml \
                        -f docker-compose.dev.yml \
                        up -d \
                        --no-build \
                        --remove-orphans \
                        --wait \
                        --wait-timeout 180

                    docker compose \
                        -p "$DEV_PROJECT" \
                        --env-file .env.dev.ci \
                        -f docker-compose.yml \
                        -f docker-compose.dev.yml \
                        ps
                '''
            }
        }

        stage('Run Tests') {
            when {
                expression {
                    env.GIT_BRANCH == 'origin/feature/jenkins-cicd' ||
                    env.GIT_BRANCH == 'feature/jenkins-cicd' ||
                    env.GIT_BRANCH == 'origin/main' ||
                    env.GIT_BRANCH == 'main'
                }
            }

            steps {
                echo 'Running health checks and smoke tests against Dev...'

                sh '''
                    set -eu

                    chmod +x tests/run-tests.sh
                    chmod +x tests/health/health-check.sh
                    chmod +x tests/smoke/smoke-test.sh

                    SERVER_HOST="$(grep '^SERVER_HOST=' .env.dev.ci | cut -d= -f2-)"

                    if [ -z "$SERVER_HOST" ]; then
                        echo "ERROR: SERVER_HOST is empty in .env.dev.ci."
                        exit 1
                    fi

                    echo "Testing against: http://${SERVER_HOST}"

                    BASE_URL="http://${SERVER_HOST}" \
                        ./tests/run-tests.sh
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
                        set -eu

                        echo "$DOCKER_TOKEN" |
                            docker login \
                                --username "$DOCKER_USER" \
                                --password-stdin
                    '''
                }
            }
        }

        stage('Push Docker Images') {
            steps {
                echo "Pushing Docker images with tag ${IMAGE_TAG}..."

                sh '''
                    set -eu

                    docker compose \
                        -p "$DEV_PROJECT" \
                        --env-file .env.dev.ci \
                        -f docker-compose.yml \
                        -f docker-compose.dev.yml \
                        push
                '''
            }
        }

        stage('Deploy Staging') {
            when {
                expression {
                    env.GIT_BRANCH == 'origin/main' ||
                    env.GIT_BRANCH == 'main'
                }
            }

            steps {
                echo "Deploying build ${BUILD_NUMBER} to Staging..."

                sh '''
                    set -eu

                    docker compose \
                        -p "$STAGING_PROJECT" \
                        --env-file .env.staging.ci \
                        -f docker-compose.yml \
                        -f docker-compose.staging.yml \
                        pull nginx wordpress prestashop

                    docker compose \
                        -p "$STAGING_PROJECT" \
                        --env-file .env.staging.ci \
                        -f docker-compose.yml \
                        -f docker-compose.staging.yml \
                        up -d \
                        --no-build \
                        --remove-orphans \
                        --wait \
                        --wait-timeout 180

                    docker compose \
                        -p "$STAGING_PROJECT" \
                        --env-file .env.staging.ci \
                        -f docker-compose.yml \
                        -f docker-compose.staging.yml \
                        ps
                '''
            }
        }

        stage('Test Staging') {
            when {
                expression {
                    env.GIT_BRANCH == 'origin/main' ||
                    env.GIT_BRANCH == 'main'
                }
            }

            steps {
                echo 'Running tests against Staging...'

                sh '''
                    set -eu

                    SERVER_HOST="$(grep '^SERVER_HOST=' .env.staging.ci | cut -d= -f2-)"

                    if [ -z "$SERVER_HOST" ]; then
                        echo "ERROR: SERVER_HOST is empty in .env.staging.ci."
                        exit 1
                    fi

                    echo "Testing Staging: http://${SERVER_HOST}"

                    BASE_URL="http://${SERVER_HOST}" \
                        ./tests/run-tests.sh
                '''
            }
        }

        stage('Production Approval') {
            when {
                expression {
                    env.GIT_BRANCH == 'origin/main' ||
                    env.GIT_BRANCH == 'main'
                }
            }

            input {
                message "Deploy build ${BUILD_NUMBER} to Production?"
                ok 'Deploy to Production'
            }

            steps {
                echo "Production deployment approved."
            }
        }

        stage('Deploy Production') {
            when {
                expression {
                    env.GIT_BRANCH == 'origin/main' ||
                    env.GIT_BRANCH == 'main'
                }
            }

            steps {
                echo "Deploying build ${BUILD_NUMBER} to Production..."

                sh '''
                    set -eu

                    docker compose \
                        -p "$PROD_PROJECT" \
                        --env-file .env.prod.ci \
                        -f docker-compose.yml \
                        -f docker-compose.prod.yml \
                        pull nginx wordpress prestashop

                    docker compose \
                        -p "$PROD_PROJECT" \
                        --env-file .env.prod.ci \
                        -f docker-compose.yml \
                        -f docker-compose.prod.yml \
                        up -d \
                        --no-build \
                        --remove-orphans \
                        --wait \
                        --wait-timeout 180

                    docker compose \
                        -p "$PROD_PROJECT" \
                        --env-file .env.prod.ci \
                        -f docker-compose.yml \
                        -f docker-compose.prod.yml \
                        ps
                '''
            }
        }

        stage('Test Production') {
            when {
                expression {
                    env.GIT_BRANCH == 'origin/main' ||
                    env.GIT_BRANCH == 'main'
                }
            }

            steps {
                echo 'Running final production health checks...'

                sh '''
                    set -eu

                    SERVER_HOST="$(grep '^SERVER_HOST=' .env.prod.ci | cut -d= -f2-)"

                    if [ -z "$SERVER_HOST" ]; then
                        echo "ERROR: SERVER_HOST is empty in .env.prod.ci."
                        exit 1
                    fi

                    echo "Testing Production: http://${SERVER_HOST}"

                    BASE_URL="http://${SERVER_HOST}" \
                        ./tests/run-tests.sh
                '''
            }
        }
    }

    post {
        success {
            echo "Pipeline completed successfully for build ${BUILD_NUMBER}."
        }

        failure {
            echo "Pipeline failed in build ${BUILD_NUMBER}. Check the failed stage logs."
        }

        always {
            sh '''
                rm -f .env.dev.ci .env.staging.ci .env.prod.ci
                docker logout >/dev/null 2>&1 || true
            '''
        }
    }
}