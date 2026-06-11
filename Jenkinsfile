pipeline {
    agent any

    environment {
        PATH = "/Library/Frameworks/Python.framework/Versions/3.14/bin:/opt/homebrew/bin:${env.PATH}"
    }

    stages {
        stage('Install Dependencies') {
            steps {
                sh 'pip3 install .'
            }
        }

        stage('Run Tests') {
            steps {
                sh 'pytest tests/ --ignore=tests/test_seed.py -s --alluredir=allure-results --clean-alluredir'
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
