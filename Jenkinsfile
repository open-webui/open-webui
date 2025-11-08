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
        stage('准备工作') {
            steps {
                script {
                    echo "========================================="
                    echo "开始构建 Build #${BUILD_NUMBER}"
                    echo "仓库: ${REPO_URL}"
                    echo "镜像: ${IMAGE_NAME}:${IMAGE_TAG}"
                    echo "========================================="
                    
                    // 检查Docker是否可用
                    sh 'docker --version'
                    sh 'docker info'
                }
            }
        }
        
        stage('检出代码') {
            steps {
                script {
                    echo "从 ${REPO_URL} 检出代码..."
                }
                
                // 使用更简单的checkout方式
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: '*/main']],
                    userRemoteConfigs: [[
                        url: "${REPO_URL}",
                        credentialsId: 'github-ssh'  // 改成你实际创建的凭据ID
                    ]]
                ])
                
                script {
                    echo "代码检出完成"
                    sh 'ls -la'
                    sh 'git log --oneline -1 || echo "无法获取git日志"'
                }
            }
        }
        
        stage('验证 Dockerfile') {
            steps {
                script {
                    echo "检查 Dockerfile..."
                    sh """
                        if [ ! -f "${DOCKER_FILE_PATH}" ]; then
                            echo "错误: 找不到 Dockerfile: ${DOCKER_FILE_PATH}"
                            echo "当前目录内容:"
                            ls -la
                            exit 1
                        fi
                        echo "Dockerfile 存在"
                        echo "--- Dockerfile 内容 (前20行) ---"
                        head -20 "${DOCKER_FILE_PATH}"
                    """
                }
            }
        }
        
        stage('创建输出目录') {
            steps {
                script {
                    echo "创建输出目录: ${OUTPUT_DIR}"
                    sh """
                        sudo mkdir -p ${OUTPUT_DIR}
                        sudo chmod 777 ${OUTPUT_DIR}
                        ls -ld ${OUTPUT_DIR}
                    """
                }
            }
        }
        
        stage('构建 Docker 镜像') {
            steps {
                script {
                    echo "开始构建镜像: ${IMAGE_NAME}:${IMAGE_TAG}"
                    sh """
                        docker build \
                            -t ${IMAGE_NAME}:${IMAGE_TAG} \
                            -t ${IMAGE_NAME}:latest \
                            -f ${DOCKER_FILE_PATH} \
                            .
                        
                        echo "镜像构建完成"
                        docker images | grep ${IMAGE_NAME} || echo "未找到镜像"
                    """
                }
            }
        }
        
        stage('导出镜像') {
            steps {
                script {
                    echo "导出镜像到 ${OUTPUT_DIR}"
                    sh """
                        echo "导出 ${IMAGE_NAME}:${IMAGE_TAG}..."
                        docker save ${IMAGE_NAME}:${IMAGE_TAG} | gzip > ${OUTPUT_DIR}/${IMAGE_NAME}-${IMAGE_TAG}.tar.gz
                        
                        echo "导出 ${IMAGE_NAME}:latest..."
                        docker save ${IMAGE_NAME}:latest | gzip > ${OUTPUT_DIR}/${IMAGE_NAME}-latest.tar.gz
                        
                        echo "导出完成"
                        ls -lh ${OUTPUT_DIR}/${IMAGE_NAME}*.tar.gz
                    """
                }
            }
        }
        
        stage('清理旧镜像') {
            steps {
                script {
                    echo "清理本地镜像..."
                    sh """
                        docker rmi ${IMAGE_NAME}:${IMAGE_TAG} 2>/dev/null || echo "镜像已删除或不存在"
                        
                        # 保留latest标签，方便下次使用
                        # docker rmi ${IMAGE_NAME}:latest 2>/dev/null || true
                        
                        # 清理悬空镜像
                        docker image prune -f --filter "dangling=true" || true
                        
                        echo "清理完成"
                    """
                }
            }
        }
    }
    
    post {
        success {
            script {
                echo "========================================="
                echo "✅ 构建成功！"
                echo "镜像文件位置: ${OUTPUT_DIR}"
                sh "ls -lh ${OUTPUT_DIR}/${IMAGE_NAME}*.tar.gz || true"
                echo "========================================="
            }
        }
        failure {
            echo "❌ 构建失败，请检查上方日志"
        }
        always {
            script {
                echo "流水线执行完成"
                // 可选：清理工作空间（注释掉以便调试）
                // cleanWs()
            }
        }
    }
}