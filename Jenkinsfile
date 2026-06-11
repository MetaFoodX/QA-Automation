pipeline {
    agent any

    parameters {
        string(name: 'BRANCH',      defaultValue: 'main',                               description: 'Git branch to build')
        choice(name: 'ENV',         choices: ['staging', 'production'],                  description: 'Target environment')
        string(name: 'BASE_URL',    defaultValue: 'https://staging-mercato.skoopin.net', description: 'Base URL of the target environment')
        choice(name: 'TEST_SUITE',  choices: ['all', 'smoke', 'regression'],             description: 'Which tests to run')
    }

    environment {
        ENV      = "${params.ENV}"
        BASE_URL = "${params.BASE_URL}"
    }

    stages {
        stage('Install Dependencies') {
            steps {
                sh 'pip3 install .'
                sh 'playwright install chromium'
            }
        }

        stage('Run Tests') {
            steps {
                withCredentials([
                    string(credentialsId: 'qa-cognito-client-id',          variable: 'COGNITO_CLIENT_ID'),
                    string(credentialsId: 'qa-api-username',               variable: 'API_USERNAME'),
                    string(credentialsId: 'qa-api-password',               variable: 'API_PASSWORD'),
                    string(credentialsId: 'qa-ui-username',                variable: 'SKOOPIN_KITCHEN_SAPNA_EMAIL'),
                    string(credentialsId: 'qa-ui-password',                variable: 'SKOOPIN_KITCHEN_SAPNA_PASSWORD'),
                ]) {
                    script {
                        def markerFlag = params.TEST_SUITE == 'all' ? '' : "-m ${params.TEST_SUITE}"
                        sh "pytest tests/ --ignore=tests/test_seed.py -s ${markerFlag} --alluredir=allure-results --clean-alluredir"
                    }
                }
            }
        }

        stage('Generate Allure Report') {
            steps {
                sh 'allure generate allure-results -o allure-report --clean --single-file'
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'allure-report/index.html', fingerprint: true
            archiveArtifacts artifacts: 'reports/junit.xml', fingerprint: true
        }
    }
}
