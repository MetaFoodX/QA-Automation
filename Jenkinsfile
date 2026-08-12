pipeline {
    agent any

    parameters {
        choice(name: 'ENV',        choices: ['staging', 'production'],                  description: 'Target environment')
        string(name: 'BASE_URL',   defaultValue: 'https://staging-mercato.skoopin.net', description: 'Base URL of the target environment')
        choice(name: 'TEST_SUITE', choices: ['all', 'smoke', 'regression'],             description: 'Which tests to run')
    }

    stages {
        stage('Fetch Deployed Branch And Commit') {
            steps {
                // Runs here (on Jenkins itself), where localhost:8080 is actually Jenkins.
                // run_qa.sh used to fetch this from the staging box, where localhost:8080
                // is staging, not Jenkins — always resolved to "unknown".
                withCredentials([usernamePassword(credentialsId: 'jenkins-branch-token', usernameVariable: 'JENKINS_USER', passwordVariable: 'JENKINS_TOKEN')]) {
                    script {
                        def info = sh(
                            script: '''
                                curl -sf -u "$JENKINS_USER:$JENKINS_TOKEN" \
                                    'http://localhost:8080/job/Build%20Staging%20Skoopin%20Server%20New/lastSuccessfulBuild/api/json?tree=actions%5BlastBuiltRevision%5BSHA1%5D,parameters%5Bname,value%5D%5D' \
                                    2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
actions = data.get('actions', [])
params = [p for a in actions for p in a.get('parameters', []) if p.get('name') == 'BRANCH_NAME']
branch = params[0]['value'].replace('origin/', '') if params else 'unknown'
revisions = [a['lastBuiltRevision']['SHA1'] for a in actions if a.get('lastBuiltRevision')]
commit = revisions[0][:8] if revisions else 'unknown'
print(f'{branch} {commit}')
" 2>/dev/null || echo "unknown unknown"
                            ''',
                            returnStdout: true
                        ).trim().split(' ')
                        env.DEPLOYED_BRANCH = info[0]
                        env.DEPLOYED_COMMIT = info[1]
                    }
                }
                echo "Deployed branch: ${env.DEPLOYED_BRANCH}, commit: ${env.DEPLOYED_COMMIT}"
            }
        }

        stage('Trigger QA on Staging') {
            steps {
                withCredentials([sshUserPrivateKey(credentialsId: 'production-server', keyFileVariable: 'SSH_KEY')]) {
                    sh """
                        scp -o StrictHostKeyChecking=no -i \$SSH_KEY run_qa.sh ubuntu@10.0.21.215:/home/ubuntu/run_qa.sh
                        ssh -o StrictHostKeyChecking=no -i \$SSH_KEY ubuntu@10.0.21.215 \
                            "bash /home/ubuntu/run_qa.sh ${params.ENV} ${params.BASE_URL} ${params.TEST_SUITE} ${BUILD_NUMBER} '${env.DEPLOYED_BRANCH}' '${env.DEPLOYED_COMMIT}'"
                    """
                }
            }
        }
    }
}
