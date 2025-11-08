pipeline {
    agent any
    
    environment {
        REPO_URL = 'git@github.com:ai-friend-coming/open-webui-next.git'
        IMAGE_NAME = 'open-webui-custom'
        IMAGE_TAG = "${BUILD_NUMBER}"
        OUTPUT_DIR = '/var/docker-images'
        DOCKER_FILE_PATH = 'Dockerfile'
    }
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 1, unit: 'HOURS')
        timestamps()
    }
    
    stages {
        stage('检出代码') {
            steps {
                script {
                    echo "🔄 从 ${REPO_URL} 检出代码..."
                }
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: '*/main']],
                    userRemoteConfigs: [[
                        url: "${REPO_URL}",
                        credentialsId: 'github-ssh-key'
                    ]],
                    extensions: [[$class: 'CloneOption', depth: 1]]
                ])
                script {
                    echo "✓ 代码检出完成"
                    sh 'git log --oneline -1'
                }
            }
        }
        
        stage('验证 Dockerfile') {
            steps {
                script {
                    sh '''
                        if [ ! -f "${DOCKER_FILE_PATH}" ]; then
                            echo "❌ 找不到 Dockerfile: ${DOCKER_FILE_PATH}"
                            ls -la
                            exit 1
                        fi
                        echo "✓ Dockerfile 存在"
                        echo "--- Dockerfile 内容预览 ---"
                        head -20 "${DOCKER_FILE_PATH}"
                    '''
                }
            }
        }
        
        stage('构建 Docker 镜像') {
            steps {
                script {
                    echo "🔨 开始构建镜像: ${IMAGE_NAME}:${IMAGE_TAG}"
                    sh '''
                        docker build \
                            -t ${IMAGE_NAME}:${IMAGE_TAG} \
                            -t ${IMAGE_NAME}:latest \
                            -f ${DOCKER_FILE_PATH} \
                            .
                        
                        echo "✓ 镜像构建完成"
                        docker images | grep ${IMAGE_NAME}
                    '''
                }
            }
        }
        
        stage('导出镜像到本地') {
            steps {
                script {
                    sh '''
                        mkdir -p ${OUTPUT_DIR}
                        
                        echo "📦 导出镜像 ${IMAGE_TAG}..."
                        docker save ${IMAGE_NAME}:${IMAGE_TAG} \
                            | gzip > ${OUTPUT_DIR}/${IMAGE_NAME}-${IMAGE_TAG}.tar.gz
                        
                        echo "📦 导出镜像 latest..."
                        docker save ${IMAGE_NAME}:latest \
                            | gzip > ${OUTPUT_DIR}/${IMAGE_NAME}-latest.tar.gz
                        
                        echo "✓ 镜像导出完成"
                        echo "--- 输出文件 ---"
                        ls -lh ${OUTPUT_DIR}/${IMAGE_NAME}*.tar.gz
                    '''
                }
            }
        }
        
        stage('清理') {
            steps {
                script {
                    sh '''
                        echo "🧹 清理本地镜像..."
                        docker rmi ${IMAGE_NAME}:${IMAGE_TAG} 2>/dev/null || true
                        docker rmi ${IMAGE_NAME}:latest 2>/dev/null || true
                        
                        # 清理悬空镜像
                        docker image prune -f --filter "dangling=true"
                        
                        echo "✓ 清理完成"
                    '''
                }
            }
        }
    }
    
    post {
        success {
            echo "✅ 构建成功！镜像已保存到 ${OUTPUT_DIR}"
        }
        failure {
            echo "❌ 构建失败，请查看日志"
        }
        always {
            cleanWs()
        }
    }
}