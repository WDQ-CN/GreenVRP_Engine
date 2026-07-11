# 京东云容器化部署指南

## 一、前置准备

### 1.1 安装 Docker Desktop
- 下载地址：https://www.docker.com/products/docker-desktop
- Windows 用户确保开启 WSL2 后端

### 1.2 注册京东云账号
- 访问：https://www.jdcloud.com
- 完成实名认证

## 二、本地构建测试

### 2.1 构建 Docker 镜像
```bash
# 进入项目目录
cd d:\ZhuoMian\Code\ITEM\GreenVRP_Engine

# 构建镜像
docker build -t greenvrp-engine:latest .

# 查看构建的镜像
docker images | grep greenvrp
```

### 2.2 本地运行测试
```bash
# 运行 FastAPI 服务
docker run -d -p 8000:8000 --name greenvrp-api greenvrp-engine:latest

# 运行 Streamlit Web 界面
docker run -d -p 8501:8501 --name greenvrp-web greenvrp-engine:latest \
  streamlit run web_app.py --server.port=8501 --server.address=0.0.0.0

# 或使用 docker-compose 启动全部服务
docker-compose up -d
```

### 2.3 验证服务
- FastAPI 文档：http://localhost:8000/docs
- Streamlit 界面：http://localhost:8501
- 健康检查：http://localhost:8000/health

## 三、推送到京东云镜像仓库

### 3.1 登录京东云容器镜像服务
```bash
# 在京东云控制台获取登录命令
# 访问：容器镜像服务 -> 实例列表 -> 登录指令

docker login -u <用户名> -p <密码> <仓库地址>
```

### 3.2 标记镜像
```bash
# 格式：docker tag 本地镜像:标签 仓库地址/命名空间/镜像名:标签
docker tag greenvrp-engine:latest <仓库地址>/greenvrp/greenvrp-engine:v1.0.0
```

### 3.3 推送镜像
```bash
docker push <仓库地址>/greenvrp/greenvrp-engine:v1.0.0
```

## 四、京东云部署方式

### 方式一：云容器引擎（Kubernetes）

#### 1. 创建 Kubernetes 集群
- 登录京东云控制台
- 进入 "云容器引擎" 服务
- 创建集群（选择合适的地域和配置）

#### 2. 部署应用
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: greenvrp-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: greenvrp-api
  template:
    metadata:
      labels:
        app: greenvrp-api
    spec:
      containers:
      - name: api
        image: <仓库地址>/greenvrp/greenvrp-engine:v1.0.0
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

```bash
# 应用部署
kubectl apply -f deployment.yaml

# 创建服务暴露
kubectl expose deployment greenvrp-api --type=LoadBalancer --port=80 --target-port=8000
```

### 方式二：容器实例服务

#### 1. 创建容器实例组
- 进入京东云 "容器实例" 服务
- 创建实例组
- 选择镜像：使用京东云镜像仓库中的镜像

#### 2. 配置参数
- 实例规格：CPU 1核 / 内存 2GB 起步
- 端口配置：8000 (API), 8501 (Web)
- 自动扩缩容：根据 CPU/内存使用率自动扩缩容

### 方式三：云服务器 + Docker

#### 1. 创建云服务器
- 进入京东云 "云主机" 服务
- 选择 CentOS 或 Ubuntu 镜像
- 配置安全组：开放 8000, 8501 端口

#### 2. 安装 Docker
```bash
# CentOS
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker

# Ubuntu
sudo apt update
sudo apt install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
```

#### 3. 部署应用
```bash
# 登录镜像仓库
sudo docker login -u <用户名> -p <密码> <仓库地址>

# 拉取镜像
sudo docker pull <仓库地址>/greenvrp/greenvrp-engine:v1.0.0

# 运行容器
sudo docker run -d -p 8000:8000 --name greenvrp-api --restart=always \
  <仓库地址>/greenvrp/greenvrp-engine:v1.0.0

# 运行 Web 界面
sudo docker run -d -p 8501:8501 --name greenvrp-web --restart=always \
  <仓库地址>/greenvrp/greenvrp-engine:v1.0.0 \
  streamlit run web_app.py --server.port=8501 --server.address=0.0.0.0
```

## 五、监控与运维

### 5.1 查看日志
```bash
# 查看容器日志
docker logs -f greenvrp-api

# Kubernetes 查看日志
kubectl logs -f deployment/greenvrp-api
```

### 5.2 更新部署
```bash
# 重新构建镜像
docker build -t greenvrp-engine:v1.0.1 .

# 推送到仓库
docker tag greenvrp-engine:v1.0.1 <仓库地址>/greenvrp/greenvrp-engine:v1.0.1
docker push <仓库地址>/greenvrp/greenvrp-engine:v1.0.1

# Kubernetes 滚动更新
kubectl set image deployment/greenvrp-api api=<仓库地址>/greenvrp/greenvrp-engine:v1.0.1
```

### 5.3 性能优化建议
1. **使用缓存层**：在 Dockerfile 中利用缓存层减少构建时间
2. **多阶段构建**：使用多阶段构建减小镜像体积
3. **资源限制**：设置合理的 CPU/内存限制，避免资源争抢
4. **健康检查**：配置 readiness 和 liveness 探针
5. **自动扩缩容**：根据负载自动调整实例数量

## 六、常见问题

### Q1: 镜像构建失败
**解决方案：**
- 检查 Dockerfile 语法
- 确保网络畅通（pip 安装依赖需要外网）
- 查看构建日志定位问题

### Q2: 容器启动后无法访问
**解决方案：**
- 检查安全组/防火墙是否开放端口
- 确认服务监听的地址是 0.0.0.0 而不是 127.0.0.1
- 查看容器日志：`docker logs <容器名>`

### Q3: 内存不足
**解决方案：**
- 增加容器内存限制
- 优化 Python 代码减少内存占用
- 使用更轻量级的基础镜像

## 七、联系方式

如有问题请联系技术支持。