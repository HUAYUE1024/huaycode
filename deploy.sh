#!/bin/bash

#============================================================
# HUAYCODE 一键部署脚本
# 支持: Docker + Nginx 自动部署
# 用法: bash deploy.sh
#============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目信息
PROJECT_NAME="HUAYCODE"
PROJECT_DIR="/opt/huaycode"
COMPOSE_PROJECT="huaycode"

# 打印带颜色的消息
print_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
print_step()    { echo -e "\n${CYAN}==>${NC} $1"; }

# 显示 Banner
show_banner() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║         HUAYCODE - Python 代码执行可视化引擎               ║"
    echo "║                   一键部署工具 v1.0                        ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查系统依赖
check_dependencies() {
    print_step "检查系统依赖"
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，正在自动安装..."
        install_docker
    fi
    print_success "Docker 已安装: $(docker --version)"
    
    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安装，正在自动安装..."
        install_docker_compose
    fi
    print_success "Docker Compose 已安装"
    
    # 检查 Docker 服务状态
    if ! docker info &> /dev/null; then
        print_warning "Docker 服务未启动，正在启动..."
        sudo systemctl start docker
        sudo systemctl enable docker
    fi
    print_success "Docker 服务运行中"
}

# 安装 Docker
install_docker() {
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        sudo apt-get update
        sudo apt-get install -y ca-certificates curl gnupg lsb-release
        sudo mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    elif [ -f /etc/redhat-release ]; then
        # CentOS/RHEL
        sudo yum install -y yum-utils
        sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    else
        print_error "不支持的操作系统，请手动安装 Docker"
        exit 1
    fi
    
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
}

# 安装 Docker Compose
install_docker_compose() {
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
}

# 获取用户输入
get_user_input() {
    print_step "配置部署参数"
    
    # 服务器 IP
    if [ -z "$SERVER_IP" ]; then
        read -p "请输入服务器 IP 地址 [默认: $(hostname -I | awk '{print $1}')]:" SERVER_IP
        SERVER_IP=${SERVER_IP:-$(hostname -I | awk '{print $1}')}
    fi
    
    # SSH 端口
    read -p "请输入 SSH 端口 [默认: 22]:" SSH_PORT
    SSH_PORT=${SSH_PORT:-22}
    
    # SSH 用户名
    read -p "请输入 SSH 用户名 [默认: root]:" SSH_USER
    SSH_USER=${SSH_USER:-root}
    
    # SSH 密码 (如果使用密码认证)
    if [ "$SSH_USER" != "root" ]; then
        read -s -p "请输入 SSH 密码:" SSH_PASSWORD
        echo
    fi
    
    # 应用端口
    read -p "请输入应用访问端口 [默认: 80]:" APP_PORT
    APP_PORT=${APP_PORT:-80}
    
    # 是否启用 SSL
    read -p "是否启用 HTTPS/SSL? (y/n) [默认: n]:" ENABLE_SSL
    ENABLE_SSL=${ENABLE_SSL:-n}
    
    echo
    print_info "部署配置摘要:"
    echo "  服务器 IP: $SERVER_IP"
    echo "  SSH 端口: $SSH_PORT"
    echo "  SSH 用户: $SSH_USER"
    echo "  应用端口: $APP_PORT"
    echo "  启用 SSL: $ENABLE_SSL"
    echo
    read -p "确认以上配置? (y/n) [默认: y]:" CONFIRM
    CONFIRM=${CONFIRM:-y}
    
    if [ "$CONFIRM" != "y" ]; then
        print_warning "部署已取消"
        exit 0
    fi
}

# 准备部署文件
prepare_deploy_files() {
    print_step "准备部署文件"
    
    # 创建临时目录
    TEMP_DIR=$(mktemp -d)
    print_info "创建临时目录: $TEMP_DIR"
    
    # 复制项目文件
    cp -r . $TEMP_DIR/
    
    # 生成环境变量文件
    cat > $TEMP_DIR/.env << EOF
# HUAYCODE 环境配置
NGINX_PORT=$APP_PORT
FLASK_ENV=production
FLASK_DEBUG=false
TZ=Asia/Shanghai
EOF
    
    # 如果启用 SSL，配置 Nginx
    if [ "$ENABLE_SSL" = "y" ]; then
        configure_ssl $TEMP_DIR
    fi
    
    print_success "部署文件准备完成"
}

# 配置 SSL
configure_ssl() {
    local dir=$1
    print_info "配置 SSL 证书..."
    
    # 创建 SSL 目录
    mkdir -p $dir/nginx/ssl
    
    # 生成自签名证书 (生产环境应使用 Let's Encrypt)
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout $dir/nginx/ssl/server.key \
        -out $dir/nginx/ssl/server.crt \
        -subj "/CN=$SERVER_IP" 2>/dev/null
    
    # 更新 Nginx 配置
    cat > $dir/nginx/conf.d/huaycode-ssl.conf << EOF
server {
    listen 443 ssl http2;
    server_name $SERVER_IP;
    
    ssl_certificate /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://huaycode:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /static/ {
        proxy_pass http://huaycode:5000;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}

server {
    listen 80;
    server_name $SERVER_IP;
    return 301 https://\$host\$request_uri;
}
EOF
    
    # 更新 docker-compose 挂载 SSL 证书
    sed -i 's|./nginx/conf.d:/etc/nginx/conf.d:ro|./nginx/conf.d:/etc/nginx/conf.d:ro\n      - ./nginx/ssl:/etc/nginx/ssl:ro|' $dir/docker-compose.yml
    
    print_success "SSL 配置完成"
}

# 上传文件到服务器
upload_to_server() {
    print_step "上传文件到服务器"
    
    # 检查 SSH 连接
    if ! ssh -p $SSH_PORT -o ConnectTimeout=10 -o StrictHostKeyChecking=no $SSH_USER@$SERVER_IP "echo 'SSH 连接成功'" &> /dev/null; then
        print_error "无法连接到服务器 $SERVER_IP:$SSH_PORT"
        exit 1
    fi
    print_success "SSH 连接测试成功"
    
    # 创建远程目录
    ssh -p $SSH_PORT $SSH_USER@$SERVER_IP "sudo mkdir -p $PROJECT_DIR && sudo chown $SSH_USER:$SSH_USER $PROJECT_DIR"
    
    # 上传文件
    print_info "正在上传文件..."
    rsync -avz -e "ssh -p $SSH_PORT" \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        $TEMP_DIR/ $SSH_USER@$SERVER_IP:$PROJECT_DIR/
    
    print_success "文件上传完成"
}

# 在服务器上执行部署
deploy_on_server() {
    print_step "在服务器上执行部署"
    
    ssh -p $SSH_PORT $SSH_USER@$SERVER_IP << EOF
        set -e
        cd $PROJECT_DIR
        
        # 停止旧容器 (如果存在)
        echo "停止旧服务..."
        docker-compose down 2>/dev/null || true
        
        # 清理旧镜像
        echo "清理旧镜像..."
        docker system prune -f
        
        # 构建并启动服务
        echo "构建并启动服务..."
        docker-compose build --no-cache
        docker-compose up -d
        
        # 等待服务启动
        echo "等待服务启动..."
        sleep 10
        
        # 检查服务状态
        if docker-compose ps | grep -q "Up"; then
            echo "✅ 服务启动成功"
        else
            echo "❌ 服务启动失败"
            docker-compose logs
            exit 1
        fi
EOF
    
    if [ $? -eq 0 ]; then
        print_success "部署成功完成"
    else
        print_error "部署失败"
        exit 1
    fi
}

# 显示部署结果
show_result() {
    print_step "部署完成"
    
    echo -e "${GREEN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║                   🎉 部署成功! 🎉                          ║"
    echo "║                                                            ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║                                                            ║"
    
    if [ "$ENABLE_SSL" = "y" ]; then
        echo "║   访问地址: https://$SERVER_IP                            "
    else
        echo "║   访问地址: http://$SERVER_IP:$APP_PORT                   "
    fi
    
    echo "║                                                            ║"
    echo "║   管理命令 (在服务器上执行):                               ║"
    echo "║     查看状态: cd $PROJECT_DIR && docker-compose ps         ║"
    echo "║     查看日志: cd $PROJECT_DIR && docker-compose logs -f    ║"
    echo "║     重启服务: cd $PROJECT_DIR && docker-compose restart    ║"
    echo "║     停止服务: cd $PROJECT_DIR && docker-compose down       ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 清理临时文件
cleanup() {
    if [ -d "$TEMP_DIR" ]; then
        rm -rf $TEMP_DIR
    fi
}

# 主函数
main() {
    show_banner
    
    # 检查是否在项目目录
    if [ ! -f "docker-compose.yml" ] || [ ! -f "Dockerfile" ]; then
        print_error "请在项目根目录下运行此脚本"
        exit 1
    fi
    
    # 设置清理钩子
    trap cleanup EXIT
    
    # 检查依赖
    check_dependencies
    
    # 获取用户输入
    get_user_input
    
    # 准备部署文件
    prepare_deploy_files
    
    # 上传到服务器
    upload_to_server
    
    # 在服务器上部署
    deploy_on_server
    
    # 显示结果
    show_result
}

# 运行主函数
main "$@"
