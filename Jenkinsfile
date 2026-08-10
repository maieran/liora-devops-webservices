pipeline {
    agent any

    environment {
        DOCKERHUB_USERNAME = 'shabbyalaei'

        DEV_PROJECT = 'liora-dev'
        STAGING_PROJECT = 'liora-staging'
        PROD_PROJECT = 'liora-prod'

        DEV_PORT = '8080'
        STAGING_PORT = '8081'
        PROD_PORT = '8082'
    }

    options {
        /*
         * Prevent concurrent executions of the same branch job.
         * Deployment locking is currently not enabled because
         * the Lockable Resources option is not available on this Jenkins.
         */
        disableConcurrentBuilds()

        timestamps()
    }

    stages {

        /*
         * Creates an immutable Docker image tag
         * from the current Git commit SHA.
         */
        stage('Pipeline Check') {
            steps {
                script {
                    env.IMAGE_TAG = sh(
                        script: 'git rev-parse --short=12 HEAD',
                        returnStdout: true
                    ).trim()
                }

                echo 'Liora CI/CD pipeline is running successfully.'
                echo "Branch: ${env.BRANCH_NAME ?: 'unknown'}"
                echo "Build number: ${BUILD_NUMBER}"
                echo "Docker image tag: ${IMAGE_TAG}"
            }
        }

        /*
         * Displays information about the Jenkins worker and verifies
         * that Docker and Docker Compose are available.
         * BRANCH_NAME is used because this project is intended
         * to run as a Jenkins Multibranch Pipeline.
         */
        stage('Environment Info') {
            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail

                    echo "Workspace: $(pwd)"
                    echo "Git branch: ${BRANCH_NAME:-unknown}"
                    echo "Build number: ${BUILD_NUMBER}"
                    echo "Image tag: ${IMAGE_TAG}"

                    docker --version
                    docker compose version
                '''
            }
        }

        /*
         * A temporary environment file is created only for this stage.
         * Jenkins credentials are not copied permanently into the workspace.
         * The temporary file is automatically deleted when the shell exits.
         */
        stage('Validate Dev Compose') {
            steps {
                withCredentials([
                    string(
                        credentialsId: 'liora-wp-db-password',
                        variable: 'WORDPRESS_DB_PASSWORD'
                    ),
                    string(
                        credentialsId: 'liora-wp-db-root-password',
                        variable: 'WORDPRESS_DB_ROOT_PASSWORD'
                    ),
                    string(
                        credentialsId: 'liora-presta-db-password',
                        variable: 'PRESTASHOP_DB_PASSWORD'
                    ),
                    string(
                        credentialsId: 'liora-presta-db-root-password',
                        variable: 'PRESTASHOP_DB_ROOT_PASSWORD'
                    )
                ]) {
                    sh '''#!/usr/bin/env bash
        set -euo pipefail

        ENV_FILE="$(mktemp)"
        chmod 600 "$ENV_FILE"

        trap 'rm -f "$ENV_FILE"' EXIT

        CURRENT_IP="$(
            curl -fsS https://checkip.amazonaws.com |
            tr -d '\\n'
        )"

        if [[ -z "$CURRENT_IP" ]]; then
            echo "ERROR: Could not detect public IP."
            exit 1
        fi

        cat > "$ENV_FILE" <<EOF
        WORDPRESS_DB_NAME=wordpress
        WORDPRESS_DB_USER=wordpress
        WORDPRESS_DB_PASSWORD=${WORDPRESS_DB_PASSWORD}
        WORDPRESS_DB_ROOT_PASSWORD=${WORDPRESS_DB_ROOT_PASSWORD}

        PRESTASHOP_DB_NAME=prestashop
        PRESTASHOP_DB_USER=prestashop
        PRESTASHOP_DB_PASSWORD=${PRESTASHOP_DB_PASSWORD}
        PRESTASHOP_DB_ROOT_PASSWORD=${PRESTASHOP_DB_ROOT_PASSWORD}

        APP_PORT=${DEV_PORT}
        SERVER_HOST=${CURRENT_IP}:${DEV_PORT}
        EOF

        docker compose \
            -p "$DEV_PROJECT" \
            --env-file "$ENV_FILE" \
            -f docker-compose.yml \
            -f docker-compose.dev.yml \
            config --quiet

        echo "Development Compose configuration is valid."
        '''
                }
            }
        }

        /*
         * Application images are built using IMAGE_TAG.
         * IMAGE_TAG contains the Git SHA and therefore identifies
         * exactly which source revision produced each image.
         */
        stage('Build Docker Images') {
            steps {
                withCredentials([
                    string(
                        credentialsId: 'liora-wp-db-password',
                        variable: 'WORDPRESS_DB_PASSWORD'
                    ),
                    string(
                        credentialsId: 'liora-wp-db-root-password',
                        variable: 'WORDPRESS_DB_ROOT_PASSWORD'
                    ),
                    string(
                        credentialsId: 'liora-presta-db-password',
                        variable: 'PRESTASHOP_DB_PASSWORD'
                    ),
                    string(
                        credentialsId: 'liora-presta-db-root-password',
                        variable: 'PRESTASHOP_DB_ROOT_PASSWORD'
                    )
                ]) {
                    sh '''#!/usr/bin/env bash
        set -euo pipefail

        ENV_FILE="$(mktemp)"
        chmod 600 "$ENV_FILE"

        trap 'rm -f "$ENV_FILE"' EXIT

        CURRENT_IP="$(
            curl -fsS https://checkip.amazonaws.com |
            tr -d '\\n'
        )"

        if [[ -z "$CURRENT_IP" ]]; then
            echo "ERROR: Could not detect public IP."
            exit 1
        fi

        cat > "$ENV_FILE" <<EOF
        WORDPRESS_DB_NAME=wordpress
        WORDPRESS_DB_USER=wordpress
        WORDPRESS_DB_PASSWORD=${WORDPRESS_DB_PASSWORD}
        WORDPRESS_DB_ROOT_PASSWORD=${WORDPRESS_DB_ROOT_PASSWORD}

        PRESTASHOP_DB_NAME=prestashop
        PRESTASHOP_DB_USER=prestashop
        PRESTASHOP_DB_PASSWORD=${PRESTASHOP_DB_PASSWORD}
        PRESTASHOP_DB_ROOT_PASSWORD=${PRESTASHOP_DB_ROOT_PASSWORD}

        APP_PORT=${DEV_PORT}
        SERVER_HOST=${CURRENT_IP}:${DEV_PORT}
        EOF

        echo "Building images with tag: ${IMAGE_TAG}"

        docker compose \
            -p "$DEV_PROJECT" \
            --env-file "$ENV_FILE" \
            -f docker-compose.yml \
            -f docker-compose.dev.yml \
            build

        echo
        echo "Built Docker images:"

        docker compose \
            -p "$DEV_PROJECT" \
            --env-file "$ENV_FILE" \
            -f docker-compose.yml \
            -f docker-compose.dev.yml \
            config --images
        '''
                }
            }
        }

        /*
         * Development deployment and tests.
         * Locking can be added later when Lockable Resources
         * support is available on Jenkins.
         */
        stage('Development Environment') {

            stages {

                stage('Deploy Dev') {
                    steps {
                        withCredentials([
                            string(
                                credentialsId: 'liora-wp-db-password',
                                variable: 'WORDPRESS_DB_PASSWORD'
                            ),
                            string(
                                credentialsId: 'liora-wp-db-root-password',
                                variable: 'WORDPRESS_DB_ROOT_PASSWORD'
                            ),
                            string(
                                credentialsId: 'liora-presta-db-password',
                                variable: 'PRESTASHOP_DB_PASSWORD'
                            ),
                            string(
                                credentialsId: 'liora-presta-db-root-password',
                                variable: 'PRESTASHOP_DB_ROOT_PASSWORD'
                            )
                        ]) {
                            sh '''#!/usr/bin/env bash
                set -euo pipefail

                ENV_FILE="$(mktemp)"
                chmod 600 "$ENV_FILE"

                trap 'rm -f "$ENV_FILE"' EXIT

                CURRENT_IP="$(
                    curl -fsS https://checkip.amazonaws.com |
                    tr -d '\\n'
                )"

                if [[ -z "$CURRENT_IP" ]]; then
                    echo "ERROR: Could not detect public IP."
                    exit 1
                fi

                cat > "$ENV_FILE" <<EOF
                WORDPRESS_DB_NAME=wordpress
                WORDPRESS_DB_USER=wordpress
                WORDPRESS_DB_PASSWORD=${WORDPRESS_DB_PASSWORD}
                WORDPRESS_DB_ROOT_PASSWORD=${WORDPRESS_DB_ROOT_PASSWORD}

                PRESTASHOP_DB_NAME=prestashop
                PRESTASHOP_DB_USER=prestashop
                PRESTASHOP_DB_PASSWORD=${PRESTASHOP_DB_PASSWORD}
                PRESTASHOP_DB_ROOT_PASSWORD=${PRESTASHOP_DB_ROOT_PASSWORD}

                APP_PORT=${DEV_PORT}
                SERVER_HOST=${CURRENT_IP}:${DEV_PORT}
                EOF

                echo "Deploying Dev image: ${IMAGE_TAG}"

                docker compose \
                    -p "$DEV_PROJECT" \
                    --env-file "$ENV_FILE" \
                    -f docker-compose.yml \
                    -f docker-compose.dev.yml \
                    up -d \
                    --no-build \
                    --remove-orphans \
                    --wait \
                    --wait-timeout 300

                docker compose \
                    -p "$DEV_PROJECT" \
                    --env-file "$ENV_FILE" \
                    -f docker-compose.yml \
                    -f docker-compose.dev.yml \
                    ps
                '''
                        }
                    }
                }

                stage('Run Dev Tests') {
                    steps {
                        sh '''#!/usr/bin/env bash
                            set -euo pipefail

                            chmod +x tests/run-tests.sh
                            chmod +x tests/health/health-check.sh
                            chmod +x tests/smoke/smoke-test.sh

                            CURRENT_IP="$(
                                curl -fsS https://checkip.amazonaws.com |
                                tr -d '\\n'
                            )"

                            BASE_URL="http://${CURRENT_IP}:${DEV_PORT}"

                            echo "Testing Dev: ${BASE_URL}"

                            BASE_URL="$BASE_URL" ./tests/run-tests.sh
                        '''
                    }
                }
            }
        }

        /*
         * Release images are published only from main.
         * Feature branches may build and test images locally,
         * but must not publish release images to Docker Hub.
         */
        stage('Docker Login') {
            when {
                branch 'main'
            }

            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'liora-dockerhub-credentials',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_TOKEN'
                    )
                ]) {
                    sh '''#!/usr/bin/env bash
                        set -euo pipefail

                        echo "$DOCKER_TOKEN" |
                            docker login \
                                --username "$DOCKER_USER" \
                                --password-stdin
                    '''
                }
            }
        }

        /*
         * Only main is allowed to publish images.
         * The immutable Git SHA tag prevents different branch
         * builds from overwriting the same Docker image tag.
         */
        stage('Push Docker Images') {
            when {
                branch 'main'
            }

            steps {
                withCredentials([
                    string(
                        credentialsId: 'liora-wp-db-password',
                        variable: 'WORDPRESS_DB_PASSWORD'
                    ),
                    string(
                        credentialsId: 'liora-wp-db-root-password',
                        variable: 'WORDPRESS_DB_ROOT_PASSWORD'
                    ),
                    string(
                        credentialsId: 'liora-presta-db-password',
                        variable: 'PRESTASHOP_DB_PASSWORD'
                    ),
                    string(
                        credentialsId: 'liora-presta-db-root-password',
                        variable: 'PRESTASHOP_DB_ROOT_PASSWORD'
                    )
                ]) {
                    sh '''#!/usr/bin/env bash
        set -euo pipefail

        ENV_FILE="$(mktemp)"
        chmod 600 "$ENV_FILE"

        trap 'rm -f "$ENV_FILE"' EXIT

        CURRENT_IP="$(
            curl -fsS https://checkip.amazonaws.com |
            tr -d '\\n'
        )"

        if [[ -z "$CURRENT_IP" ]]; then
            echo "ERROR: Could not detect public IP."
            exit 1
        fi

        cat > "$ENV_FILE" <<EOF
        WORDPRESS_DB_NAME=wordpress
        WORDPRESS_DB_USER=wordpress
        WORDPRESS_DB_PASSWORD=${WORDPRESS_DB_PASSWORD}
        WORDPRESS_DB_ROOT_PASSWORD=${WORDPRESS_DB_ROOT_PASSWORD}

        PRESTASHOP_DB_NAME=prestashop
        PRESTASHOP_DB_USER=prestashop
        PRESTASHOP_DB_PASSWORD=${PRESTASHOP_DB_PASSWORD}
        PRESTASHOP_DB_ROOT_PASSWORD=${PRESTASHOP_DB_ROOT_PASSWORD}

        APP_PORT=${DEV_PORT}
        SERVER_HOST=${CURRENT_IP}:${DEV_PORT}
        EOF

        echo "Pushing Docker image tag: ${IMAGE_TAG}"

        docker compose \
            -p "$DEV_PROJECT" \
            --env-file "$ENV_FILE" \
            -f docker-compose.yml \
            -f docker-compose.dev.yml \
            push
        '''
                }
            }
        }

        /*
         * Staging is deployed only from main.
         * Deployment locking can be added later when supported
         * by the Jenkins installation.
         */
        stage('Staging Environment') {
            when {
                branch 'main'
            }

            stages {

                stage('Deploy Staging') {
                    steps {
                        withCredentials([
                            string(
                                credentialsId: 'liora-wp-db-password',
                                variable: 'WORDPRESS_DB_PASSWORD'
                            ),
                            string(
                                credentialsId: 'liora-wp-db-root-password',
                                variable: 'WORDPRESS_DB_ROOT_PASSWORD'
                            ),
                            string(
                                credentialsId: 'liora-presta-db-password',
                                variable: 'PRESTASHOP_DB_PASSWORD'
                            ),
                            string(
                                credentialsId: 'liora-presta-db-root-password',
                                variable: 'PRESTASHOP_DB_ROOT_PASSWORD'
                            )
                        ]) {
                            sh '''#!/usr/bin/env bash
                set -euo pipefail

                ENV_FILE="$(mktemp)"
                chmod 600 "$ENV_FILE"

                trap 'rm -f "$ENV_FILE"' EXIT

                CURRENT_IP="$(
                    curl -fsS https://checkip.amazonaws.com |
                    tr -d '\\n'
                )"

                if [[ -z "$CURRENT_IP" ]]; then
                    echo "ERROR: Could not detect public IP."
                    exit 1
                fi

                cat > "$ENV_FILE" <<EOF
                WORDPRESS_DB_NAME=wordpress
                WORDPRESS_DB_USER=wordpress
                WORDPRESS_DB_PASSWORD=${WORDPRESS_DB_PASSWORD}
                WORDPRESS_DB_ROOT_PASSWORD=${WORDPRESS_DB_ROOT_PASSWORD}

                PRESTASHOP_DB_NAME=prestashop
                PRESTASHOP_DB_USER=prestashop
                PRESTASHOP_DB_PASSWORD=${PRESTASHOP_DB_PASSWORD}
                PRESTASHOP_DB_ROOT_PASSWORD=${PRESTASHOP_DB_ROOT_PASSWORD}

                APP_PORT=${STAGING_PORT}
                SERVER_HOST=${CURRENT_IP}:${STAGING_PORT}
                EOF

                docker compose \
                    -p "$STAGING_PROJECT" \
                    --env-file "$ENV_FILE" \
                    -f docker-compose.yml \
                    -f docker-compose.staging.yml \
                    config --quiet

                echo "Deploying ${IMAGE_TAG} to Staging."

                docker compose \
                    -p "$STAGING_PROJECT" \
                    --env-file "$ENV_FILE" \
                    -f docker-compose.yml \
                    -f docker-compose.staging.yml \
                    pull nginx wordpress prestashop

                docker compose \
                    -p "$STAGING_PROJECT" \
                    --env-file "$ENV_FILE" \
                    -f docker-compose.yml \
                    -f docker-compose.staging.yml \
                    up -d \
                    --no-build \
                    --remove-orphans \
                    --wait \
                    --wait-timeout 300

                docker compose \
                    -p "$STAGING_PROJECT" \
                    --env-file "$ENV_FILE" \
                    -f docker-compose.yml \
                    -f docker-compose.staging.yml \
                    ps
                '''
                        }
                    }
                }

                stage('Test Staging') {
                    steps {
                        sh '''#!/usr/bin/env bash
                            set -euo pipefail

                            CURRENT_IP="$(
                                curl -fsS https://checkip.amazonaws.com |
                                tr -d '\\n'
                            )"

                            BASE_URL="http://${CURRENT_IP}:${STAGING_PORT}"

                            echo "Testing Staging: ${BASE_URL}"

                            BASE_URL="$BASE_URL" ./tests/run-tests.sh
                        '''
                    }
                }
            }
        }

        /*
         * Production is available only from main.
         * The timeout prevents the pipeline from waiting
         * indefinitely for human approval.
         */
        stage('Production Approval') {
            when {
                beforeInput true
                branch 'main'
            }

            options {
                timeout(
                    time: 30,
                    unit: 'MINUTES'
                )
            }

            input {
                message 'Deploy the current validated image to Production?'
                ok 'Deploy to Production'
            }

            steps {
                echo "Production deployment approved for ${IMAGE_TAG}."
            }
        }

        /*
         * Production deployment and tests.
         * Deployment locking can be added later when supported
         * by the Jenkins installation.
         */
        stage('Production Environment') {
            when {
                branch 'main'
            }

            stages {
                stage('Deploy Production') {
                    steps {
                        withCredentials([
                            string(
                                credentialsId: 'liora-wp-db-password',
                                variable: 'WORDPRESS_DB_PASSWORD'
                            ),
                            string(
                                credentialsId: 'liora-wp-db-root-password',
                                variable: 'WORDPRESS_DB_ROOT_PASSWORD'
                            ),
                            string(
                                credentialsId: 'liora-presta-db-password',
                                variable: 'PRESTASHOP_DB_PASSWORD'
                            ),
                            string(
                                credentialsId: 'liora-presta-db-root-password',
                                variable: 'PRESTASHOP_DB_ROOT_PASSWORD'
                            )
                        ]) {
                            sh '''#!/usr/bin/env bash
                set -euo pipefail

                ENV_FILE="$(mktemp)"
                chmod 600 "$ENV_FILE"

                trap 'rm -f "$ENV_FILE"' EXIT

                CURRENT_IP="$(
                    curl -fsS https://checkip.amazonaws.com |
                    tr -d '\\n'
                )"

                if [[ -z "$CURRENT_IP" ]]; then
                    echo "ERROR: Could not detect public IP."
                    exit 1
                fi

                cat > "$ENV_FILE" <<EOF
                WORDPRESS_DB_NAME=wordpress
                WORDPRESS_DB_USER=wordpress
                WORDPRESS_DB_PASSWORD=${WORDPRESS_DB_PASSWORD}
                WORDPRESS_DB_ROOT_PASSWORD=${WORDPRESS_DB_ROOT_PASSWORD}

                PRESTASHOP_DB_NAME=prestashop
                PRESTASHOP_DB_USER=prestashop
                PRESTASHOP_DB_PASSWORD=${PRESTASHOP_DB_PASSWORD}
                PRESTASHOP_DB_ROOT_PASSWORD=${PRESTASHOP_DB_ROOT_PASSWORD}

                APP_PORT=${PROD_PORT}
                SERVER_HOST=${CURRENT_IP}:${PROD_PORT}
                EOF

                docker compose \
                    -p "$PROD_PROJECT" \
                    --env-file "$ENV_FILE" \
                    -f docker-compose.yml \
                    -f docker-compose.prod.yml \
                    config --quiet

                echo "Deploying ${IMAGE_TAG} to Production."

                docker compose \
                    -p "$PROD_PROJECT" \
                    --env-file "$ENV_FILE" \
                    -f docker-compose.yml \
                    -f docker-compose.prod.yml \
                    pull nginx wordpress prestashop

                docker compose \
                    -p "$PROD_PROJECT" \
                    --env-file "$ENV_FILE" \
                    -f docker-compose.yml \
                    -f docker-compose.prod.yml \
                    up -d \
                    --no-build \
                    --remove-orphans \
                    --wait \
                    --wait-timeout 300

                docker compose \
                    -p "$PROD_PROJECT" \
                    --env-file "$ENV_FILE" \
                    -f docker-compose.yml \
                    -f docker-compose.prod.yml \
                    ps
                '''
                        }
                    }
                }

                stage('Test Production') {
                    steps {
                        sh '''#!/usr/bin/env bash
                            set -euo pipefail

                            CURRENT_IP="$(
                                curl -fsS https://checkip.amazonaws.com |
                                tr -d '\\n'
                            )"

                            BASE_URL="http://${CURRENT_IP}:${PROD_PORT}"

                            echo "Testing Production: ${BASE_URL}"

                            BASE_URL="$BASE_URL" ./tests/run-tests.sh
                        '''
                    }
                }
            }
        }
    }

    /*
     * Docker authentication is removed regardless of whether
     * the pipeline succeeds or fails.
     * Temporary environment files use mktemp plus trap and
     * are removed inside the stage that created them.
     */
    post {

        success {
            echo 'Pipeline completed successfully.'
            echo "Branch: ${env.BRANCH_NAME ?: 'unknown'}"
            echo "Image: ${env.IMAGE_TAG ?: 'unknown'}"
        }

        failure {
            echo 'Pipeline failed.'
            echo 'Check the failed Jenkins stage logs.'
        }

        always {
            sh '''#!/usr/bin/env bash
                set +e

                docker logout >/dev/null 2>&1 || true

                # Cleanup files from the previous pipeline
                # implementation if they still exist.
                rm -f \
                    .env.dev.ci \
                    .env.staging.ci \
                    .env.prod.ci
            '''
        }
    }
}