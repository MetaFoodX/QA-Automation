pipeline {
    agent any

    parameters {
        string(name: 'BRANCH',     defaultValue: 'main',                               description: 'Git branch to build')
        choice(name: 'ENV',        choices: ['staging', 'production'],                  description: 'Target environment')
        string(name: 'BASE_URL',   defaultValue: 'https://staging-mercato.skoopin.net', description: 'Base URL of the target environment')
        choice(name: 'TEST_SUITE', choices: ['all', 'smoke', 'regression'],             description: 'Which tests to run')
    }

    stages {
        stage('Checkout') {
            steps {
                cleanWs()
                git branch: "${params.BRANCH}",
                    credentialsId: 'git',
                    url: 'https://github.com/MetaFoodX/QA-Automation'
            }
        }

        stage('Build CI Image') {
            steps {
                sh 'docker build -t qa-automation-ci -f Dockerfile.ci .'
            }
        }

        stage('Run Tests') {
            steps {
                withCredentials([
                    string(credentialsId: 'qa-cognito-client-id', variable: 'COGNITO_CLIENT_ID'),
                    string(credentialsId: 'qa-api-username',      variable: 'API_USERNAME'),
                    string(credentialsId: 'qa-api-password',      variable: 'API_PASSWORD'),
                    string(credentialsId: 'qa-ui-username',       variable: 'SKOOPIN_KITCHEN_SAPNA_EMAIL'),
                    string(credentialsId: 'qa-ui-password',       variable: 'SKOOPIN_KITCHEN_SAPNA_PASSWORD'),
                    usernamePassword(credentialsId: 'jenkins-branch-token',
                                     usernameVariable: 'JENKINS_USER',
                                     passwordVariable: 'JENKINS_TOKEN'),
                ]) {
                    script {
                        def markerFlag = params.TEST_SUITE == 'all' ? '' : "-m ${params.TEST_SUITE}"
                        def deployedBranch = sh(
                            script: '''
                                RESULT=$(curl -sf -u "$JENKINS_USER:$JENKINS_TOKEN" 'http://localhost:8999/job/Build%20Staging%20Skoopin%20Server%20New/lastSuccessfulBuild/api/json?tree=actions%5Bparameters%5Bname%2Cvalue%5D%5D' 2>/dev/null) || true
                                if [ -z "$RESULT" ]; then echo "unknown"; exit 0; fi
                                echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
params = [p for a in data.get('actions', []) for p in a.get('parameters', []) if p.get('name') == 'BRANCH_NAME']
print(params[0]['value'].replace('origin/', '') if params else 'unknown')
" 2>/dev/null || echo "unknown"
                            ''',
                            returnStdout: true
                        ).trim()
                        writeFile file: 'run_tests.sh', text: """\
#!/usr/bin/env bash
pip install .
playwright install chromium
pytest dashboard/tests/ --ignore=dashboard/tests/test_seed.py -s ${markerFlag} --alluredir=allure-results --clean-alluredir
PYTEST_EXIT=\$?
allure generate allure-results -o allure-report --clean --single-file
exit \$PYTEST_EXIT
"""
                        sh """
                            chmod +x run_tests.sh

                            CID=\$(docker create \\
                                -w /workspace \\
                                -e ENV='${params.ENV}' \\
                                -e BASE_URL='${params.BASE_URL}' \\
                                -e COGNITO_CLIENT_ID="\$COGNITO_CLIENT_ID" \\
                                -e API_USERNAME="\$API_USERNAME" \\
                                -e API_PASSWORD="\$API_PASSWORD" \\
                                -e SKOOPIN_KITCHEN_SAPNA_EMAIL="\$SKOOPIN_KITCHEN_SAPNA_EMAIL" \\
                                -e SKOOPIN_KITCHEN_SAPNA_PASSWORD="\$SKOOPIN_KITCHEN_SAPNA_PASSWORD" \\
                                -e DEPLOYED_BRANCH='${deployedBranch}' \\
                                qa-automation-ci bash /workspace/run_tests.sh)

                            docker cp "\$WORKSPACE/." "\$CID:/workspace"
                            docker start \$CID
                            EXIT=\$(docker wait \$CID)
                            docker logs \$CID
                            docker cp \$CID:/workspace/allure-results . 2>/dev/null || true
                            docker cp \$CID:/workspace/allure-report  . 2>/dev/null || true
                            docker cp \$CID:/workspace/reports        . 2>/dev/null || true
                            docker rm \$CID
                            exit \$EXIT
                        """
                    }
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/outcomes/*/allure-report/index.html, reports/outcomes/*/test_results.xlsx', fingerprint: true, allowEmptyArchive: true
        }
    }
}
