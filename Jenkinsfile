pipeline {
    agent any

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
                    string(credentialsId: 'env',                          variable: 'ENV'),
                    string(credentialsId: 'base-url',                     variable: 'BASE_URL'),
                    string(credentialsId: 'cognito-client-id',            variable: 'COGNITO_CLIENT_ID'),
                    string(credentialsId: 'api-username',                 variable: 'API_USERNAME'),
                    string(credentialsId: 'api-password',                 variable: 'API_PASSWORD'),
                    string(credentialsId: 'skoopin-kitchen-sapna-email',  variable: 'SKOOPIN_KITCHEN_SAPNA_EMAIL'),
                    string(credentialsId: 'skoopin-kitchen-sapna-password', variable: 'SKOOPIN_KITCHEN_SAPNA_PASSWORD'),
                ]) {
                    sh 'pytest tests/ --ignore=tests/test_seed.py -s --alluredir=allure-results --clean-alluredir'
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
