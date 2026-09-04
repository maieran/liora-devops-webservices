pipeline {
    agent any

    environment {
        K8S_HOST = '10.10.10.11'

        DOCKERHUB_USERNAME = 'shabbyalaei'

        DEV_PROJECT = 'liora-dev'
        STAGING_PROJECT = 'liora-staging'
        PROD_PROJECT = 'liora-prod'

        DEFAULT_DEV_PORT = '8080'
        DEFAULT_STAGING_PORT = '8081'
        DEFAULT_PROD_PORT = '8082'
    }

    options {
        /*
         * Prevent concurrent executions of the same branch job.
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
                    helm version --short
                    kubectl version --client
                    kubectl cluster-info
                '''
            }
        }

                /*
         * Validates the Helm chart for all environments
         * before any deployment is started.
         */
        stage('Validate Helm Charts') {
            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail

                    for ENV in dev staging prod; do
                        echo "===== Validating Helm: ${ENV} ====="

                        helm lint \
                            ./helm/liora \
                            -f "helm/liora/values-${ENV}.yaml" \
                            --set "prestashop.publicHost=${ENV}.example.test"

                        helm template "liora-${ENV}" \
                            ./helm/liora \
                            --namespace "liora-${ENV}" \
                            -f "helm/liora/values-${ENV}.yaml" \
                            --set "prestashop.publicHost=${ENV}.example.test" \
                            > /dev/null
                    done

                    echo "All Helm charts validated successfully."
                '''
            }
        }

        /*
         * Resolve deployment host and ports once for the complete pipeline.
         *
         * If overrides exist, Jenkins uses them.
         * Otherwise the public IP and default ports are used.
         *
         * Example for the Proxmox Jenkins VM:
         *
         * CI_HOST_OVERRIDE=127.0.0.1
         * DEV_PORT_OVERRIDE=8088
         * STAGING_PORT_OVERRIDE=8089
         * PROD_PORT_OVERRIDE=8090
         *
         * On another VM without overrides:
         *
         * RUNTIME_HOST=<public IP>
         * DEV_PORT=8080
         * STAGING_PORT=8081
         * PROD_PORT=8082
         */
        stage('Resolve Runtime Configuration') {
            steps {
                script {
                    if (env.CI_HOST_OVERRIDE?.trim()) {
                        env.RUNTIME_HOST = env.CI_HOST_OVERRIDE.trim()

                        echo 'Using configured CI host override.'
                    } else {
                        env.RUNTIME_HOST = sh(
                            script: '''
                                curl -fsS https://checkip.amazonaws.com |
                                    tr -d '\\n'
                            ''',
                            returnStdout: true
                        ).trim()

                        if (!env.RUNTIME_HOST) {
                            error('Could not determine runtime host.')
                        }

                        echo 'No CI host override configured; using detected public IP.'
                    }

                    env.DEV_PORT = env.DEV_PORT_OVERRIDE?.trim()
                        ? env.DEV_PORT_OVERRIDE.trim()
                        : env.DEFAULT_DEV_PORT

                    env.STAGING_PORT = env.STAGING_PORT_OVERRIDE?.trim()
                        ? env.STAGING_PORT_OVERRIDE.trim()
                        : env.DEFAULT_STAGING_PORT

                    env.PROD_PORT = env.PROD_PORT_OVERRIDE?.trim()
                        ? env.PROD_PORT_OVERRIDE.trim()
                        : env.DEFAULT_PROD_PORT

                    echo "Runtime host: ${env.RUNTIME_HOST}"
                    echo "Dev endpoint: http://${env.RUNTIME_HOST}:${env.DEV_PORT}"
                    echo "Staging endpoint: http://${env.RUNTIME_HOST}:${env.STAGING_PORT}"
                    echo "Production endpoint: http://${env.RUNTIME_HOST}:${env.PROD_PORT}"
                }
            }
        }

        /*
         * Validates the development Docker Compose configuration.
         * Secrets exist only inside the temporary environment file.
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

                        printf '%s\\n' \
                            "WORDPRESS_DB_NAME=wordpress" \
                            "WORDPRESS_DB_USER=wordpress" \
                            "WORDPRESS_DB_PASSWORD=${WORDPRESS_DB_PASSWORD}" \
                            "WORDPRESS_DB_ROOT_PASSWORD=${WORDPRESS_DB_ROOT_PASSWORD}" \
                            "" \
                            "PRESTASHOP_DB_NAME=prestashop" \
                            "PRESTASHOP_DB_USER=prestashop" \
                            "PRESTASHOP_DB_PASSWORD=${PRESTASHOP_DB_PASSWORD}" \
                            "PRESTASHOP_DB_ROOT_PASSWORD=${PRESTASHOP_DB_ROOT_PASSWORD}" \
                            "" \
                            "APP_PORT=${DEV_PORT}" \
                            "SERVER_HOST=${RUNTIME_HOST}:${DEV_PORT}" \
                            > "$ENV_FILE"

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
         * Build application images using the immutable Git SHA tag.
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

                        printf '%s\\n' \
                            "WORDPRESS_DB_NAME=wordpress" \
                            "WORDPRESS_DB_USER=wordpress" \
                            "WORDPRESS_DB_PASSWORD=${WORDPRESS_DB_PASSWORD}" \
                            "WORDPRESS_DB_ROOT_PASSWORD=${WORDPRESS_DB_ROOT_PASSWORD}" \
                            "" \
                            "PRESTASHOP_DB_NAME=prestashop" \
                            "PRESTASHOP_DB_USER=prestashop" \
                            "PRESTASHOP_DB_PASSWORD=${PRESTASHOP_DB_PASSWORD}" \
                            "PRESTASHOP_DB_ROOT_PASSWORD=${PRESTASHOP_DB_ROOT_PASSWORD}" \
                            "" \
                            "APP_PORT=${DEV_PORT}" \
                            "SERVER_HOST=${RUNTIME_HOST}:${DEV_PORT}" \
                            > "$ENV_FILE"

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

                                printf '%s\\n' \
                                    "WORDPRESS_DB_NAME=wordpress" \
                                    "WORDPRESS_DB_USER=wordpress" \
                                    "WORDPRESS_DB_PASSWORD=${WORDPRESS_DB_PASSWORD}" \
                                    "WORDPRESS_DB_ROOT_PASSWORD=${WORDPRESS_DB_ROOT_PASSWORD}" \
                                    "" \
                                    "PRESTASHOP_DB_NAME=prestashop" \
                                    "PRESTASHOP_DB_USER=prestashop" \
                                    "PRESTASHOP_DB_PASSWORD=${PRESTASHOP_DB_PASSWORD}" \
                                    "PRESTASHOP_DB_ROOT_PASSWORD=${PRESTASHOP_DB_ROOT_PASSWORD}" \
                                    "" \
                                    "APP_PORT=${DEV_PORT}" \
                                    "SERVER_HOST=${RUNTIME_HOST}:${DEV_PORT}" \
                                    > "$ENV_FILE"

                                echo "Deploying Dev image: ${IMAGE_TAG}"
                                echo "Dev endpoint: http://${RUNTIME_HOST}:${DEV_PORT}"

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

                            BASE_URL="http://${RUNTIME_HOST}:${DEV_PORT}"

                            echo "Testing Dev: ${BASE_URL}"

                            BASE_URL="$BASE_URL" ./tests/run-tests.sh
                        '''
                    }
                }
            }
        }

        /*
         * Release images are published only from main.
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
         * Only main publishes Docker images.
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

                        printf '%s\\n' \
                            "WORDPRESS_DB_NAME=wordpress" \
                            "WORDPRESS_DB_USER=wordpress" \
                            "WORDPRESS_DB_PASSWORD=${WORDPRESS_DB_PASSWORD}" \
                            "WORDPRESS_DB_ROOT_PASSWORD=${WORDPRESS_DB_ROOT_PASSWORD}" \
                            "" \
                            "PRESTASHOP_DB_NAME=prestashop" \
                            "PRESTASHOP_DB_USER=prestashop" \
                            "PRESTASHOP_DB_PASSWORD=${PRESTASHOP_DB_PASSWORD}" \
                            "PRESTASHOP_DB_ROOT_PASSWORD=${PRESTASHOP_DB_ROOT_PASSWORD}" \
                            "" \
                            "APP_PORT=${DEV_PORT}" \
                            "SERVER_HOST=${RUNTIME_HOST}:${DEV_PORT}" \
                            > "$ENV_FILE"

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
         * Deploys the current release image to Kubernetes Dev via Helm.
         */
        stage('Deploy Kubernetes Dev') {
            when {
                branch 'main'
            }

            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail

                    echo "Deploying ${IMAGE_TAG} to Kubernetes Dev."

                    helm upgrade --install liora-dev \
                        ./helm/liora \
                        --namespace liora-dev \
                        -f helm/liora/values-dev.yaml \
                        --set "prestashop.publicHost=${K8S_HOST}" \
                        --set "nginx.image.repository=${DOCKERHUB_USERNAME}/liora-nginx" \
                        --set "nginx.image.tag=${IMAGE_TAG}" \
                        --set "wordpress.image.repository=${DOCKERHUB_USERNAME}/liora-wordpress" \
                        --set "wordpress.image.tag=${IMAGE_TAG}" \
                        --set "prestashop.image.repository=${DOCKERHUB_USERNAME}/liora-prestashop" \
                        --set "prestashop.image.tag=${IMAGE_TAG}" \
                        --set networkPolicy.enabled=true \
                        --wait \
                        --timeout 6m

                    kubectl rollout status deployment/nginx-deployment \
                        -n liora-dev \
                        --timeout=6m

                    kubectl rollout status deployment/wordpress-app \
                        -n liora-dev \
                        --timeout=6m

                    kubectl rollout status deployment/prestashop-app \
                        -n liora-dev \
                        --timeout=6m

                    echo "Kubernetes Dev deployment completed."
                '''
            }
        }

        /*
         * Validates the Kubernetes Dev deployment through the public Nginx endpoint.
         */
        stage('Test Kubernetes Dev') {
            when {
                branch 'main'
            }

            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail

                    chmod +x tests/kubernetes/validate-deployment.sh

                    ./tests/kubernetes/validate-deployment.sh \
                        liora-dev \
                        http://${K8S_HOST}:30080
                '''
            }
        }

        /*
        * Deploys the monitoring stack after the Kubernetes Dev deployment.
        */
        stage('Deploy Monitoring') {
            when {
                branch 'main'
            }

            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail

                    chmod +x monitoring/deploy-monitoring.sh
                    bash monitoring/deploy-monitoring.sh liora
                '''
            }
        }

        /*
         * Validates the monitoring stack after the Kubernetes Dev deployment.
         */
        stage('Validate Monitoring') {
            when {
                branch 'main'
            }

            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail

                    chmod +x monitoring/validate-monitoring.sh

                    bash monitoring/validate-monitoring.sh
                '''
            }
        }

        /*
         * Staging is deployed only from main.
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

                                printf '%s\\n' \
                                    "WORDPRESS_DB_NAME=wordpress" \
                                    "WORDPRESS_DB_USER=wordpress" \
                                    "WORDPRESS_DB_PASSWORD=${WORDPRESS_DB_PASSWORD}" \
                                    "WORDPRESS_DB_ROOT_PASSWORD=${WORDPRESS_DB_ROOT_PASSWORD}" \
                                    "" \
                                    "PRESTASHOP_DB_NAME=prestashop" \
                                    "PRESTASHOP_DB_USER=prestashop" \
                                    "PRESTASHOP_DB_PASSWORD=${PRESTASHOP_DB_PASSWORD}" \
                                    "PRESTASHOP_DB_ROOT_PASSWORD=${PRESTASHOP_DB_ROOT_PASSWORD}" \
                                    "" \
                                    "APP_PORT=${STAGING_PORT}" \
                                    "SERVER_HOST=${RUNTIME_HOST}:${STAGING_PORT}" \
                                    > "$ENV_FILE"

                                docker compose \
                                    -p "$STAGING_PROJECT" \
                                    --env-file "$ENV_FILE" \
                                    -f docker-compose.yml \
                                    -f docker-compose.staging.yml \
                                    config --quiet

                                echo "Deploying ${IMAGE_TAG} to Staging."
                                echo "Staging endpoint: http://${RUNTIME_HOST}:${STAGING_PORT}"

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

                            BASE_URL="http://${RUNTIME_HOST}:${STAGING_PORT}"

                            echo "Testing Staging: ${BASE_URL}"

                            BASE_URL="$BASE_URL" ./tests/run-tests.sh
                        '''
                    }
                }
            }
        }

        /*
         * Production is available only from main.
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

                                printf '%s\\n' \
                                    "WORDPRESS_DB_NAME=wordpress" \
                                    "WORDPRESS_DB_USER=wordpress" \
                                    "WORDPRESS_DB_PASSWORD=${WORDPRESS_DB_PASSWORD}" \
                                    "WORDPRESS_DB_ROOT_PASSWORD=${WORDPRESS_DB_ROOT_PASSWORD}" \
                                    "" \
                                    "PRESTASHOP_DB_NAME=prestashop" \
                                    "PRESTASHOP_DB_USER=prestashop" \
                                    "PRESTASHOP_DB_PASSWORD=${PRESTASHOP_DB_PASSWORD}" \
                                    "PRESTASHOP_DB_ROOT_PASSWORD=${PRESTASHOP_DB_ROOT_PASSWORD}" \
                                    "" \
                                    "APP_PORT=${PROD_PORT}" \
                                    "SERVER_HOST=${RUNTIME_HOST}:${PROD_PORT}" \
                                    > "$ENV_FILE"

                                docker compose \
                                    -p "$PROD_PROJECT" \
                                    --env-file "$ENV_FILE" \
                                    -f docker-compose.yml \
                                    -f docker-compose.prod.yml \
                                    config --quiet

                                echo "Deploying ${IMAGE_TAG} to Production."
                                echo "Production endpoint: http://${RUNTIME_HOST}:${PROD_PORT}"

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

                            BASE_URL="http://${RUNTIME_HOST}:${PROD_PORT}"

                            echo "Testing Production: ${BASE_URL}"

                            BASE_URL="$BASE_URL" ./tests/run-tests.sh
                        '''
                    }
                }
            }
        }
    }

    /*
     * Docker authentication is removed regardless of pipeline result.
     * Temporary environment files are deleted by their individual traps.
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