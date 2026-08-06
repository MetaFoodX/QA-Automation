pipeline {
    agent any

    parameters {
        choice(name: 'ENV',        choices: ['staging', 'production'],                  description: 'Target environment')
        string(name: 'BASE_URL',   defaultValue: 'https://staging-mercato.skoopin.net', description: 'Base URL of the target environment')
        choice(name: 'TEST_SUITE', choices: ['all', 'smoke', 'regression'],             description: 'Which tests to run')
    }

    stages {
        stage('Trigger QA on Staging') {
            steps {
                sshagent(['ubuntu']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ubuntu@10.0.21.215 \
                            "bash /home/ubuntu/run_qa.sh ${params.ENV} ${params.BASE_URL} ${params.TEST_SUITE} ${BUILD_NUMBER}"
                    """
                }
            }
        }
    }
}
