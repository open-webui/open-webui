pipeline {
  agent any
  environment {
    def IMAGE = getImage(env.GIT_BRANCH)
    def INFO_SERVER_IP = getServerIp(env.GIT_BRANCH)
    def SERVER_USER = getServerUser(env.GIT_BRANCH)
    GITHUB_ACCOUNT = credentials('GITHUB_ACCOUNT')
    def DEPLOY_ROOT_PATH = getDeployRootPath(env.GIT_BRANCH)
  }

  stages {
    stage('build and push docker image') {
      steps {
        sh "docker build -t open-webui-tmp-${env.BUILD_NUMBER} ."
      }
	  }

    stage('push docker image') {
      when {
        anyOf {
          expression { env.GIT_BRANCH == 'origin/develop' }
          expression { env.GIT_BRANCH == 'origin/staging' }
          expression { env.GIT_BRANCH == 'origin/main' }
        }
      }
      steps {
        sh "docker tag open-webui-tmp-${env.BUILD_NUMBER} ${env.IMAGE}"
        sh "echo $GITHUB_ACCOUNT_PSW | docker login --username dichhatto --password-stdin ghcr.io"
        sh "docker push ${env.IMAGE}"
      }
	  }

    stage("deploy services") {
      when {
        anyOf {
          expression { env.GIT_BRANCH == 'origin/develop' }
          expression { env.GIT_BRANCH == 'origin/staging' }
          expression { env.GIT_BRANCH == 'origin/main' }
        }
      }
      steps {
        sshagent(credentials: ['JENKINS_PRIVATE_SSH_KEY']) {
          sh "ssh ${env.SERVER_USER}@${env.INFO_SERVER_IP} docker pull ${env.IMAGE}"
          sh "ssh ${env.SERVER_USER}@${env.INFO_SERVER_IP} docker compose -f ${env.DEPLOY_ROOT_PATH}/docker-compose.yml up -d"
          sh "ssh ${env.SERVER_USER}@${env.INFO_SERVER_IP} docker compose -f ${env.DEPLOY_ROOT_PATH}/docker-compose.yml restart nginx"
        }
      }
    }
  }
}

def getServerIp(branch) {
  switch(branch) {
    case 'origin/main':
      return '118.69.81.92'
    case 'origin/staging':
      return '42.119.139.158'
    case 'origin/develop':
      return '42.119.139.158'
  }
}

def getServerUser(branch) {
  switch(branch) {
    case 'origin/main':
      return 'steve'
    case 'origin/staging':
      return 'ubuntu'
    case 'origin/develop':
      return 'ubuntu'
  }
}

def getDeployRootPath(branch) {
  switch(branch) {
    case 'origin/main':
      return '/mnt/data02/deployment/llm'
    case 'origin/staging':
      return '/home/ubuntu/deployment/llm'
    default:
      return '/home/ubuntu/deployment/dev_llm'
  }
}

def getImage(branch) {
  switch(branch) {
    case 'origin/main':
      return 'ghcr.io/hatto-nqrt/open-webui:prod'
    case 'origin/staging':
      return 'ghcr.io/hatto-nqrt/open-webui:staging'
    default:
      return 'ghcr.io/hatto-nqrt/open-webui:dev'
  }
}