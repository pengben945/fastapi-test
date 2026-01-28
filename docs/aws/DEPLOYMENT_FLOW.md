# AWS 部署与连接全流程（指令清单）

本文件汇总从部署、发布、到外网访问与验证的完整指令，适用于本项目当前架构：
EC2 + Docker Compose + Nginx(HTTPS Basic Auth) + 自签证书。

---

## 1. EC2 基础准备

### 登录
```bash
ssh -i /path/to/LogPulse-HR.pem ubuntu@<EC2_PUBLIC_IP>
```

### 安装 Docker 与 Git
```bash
sudo apt update -y
sudo apt install -y docker.io git
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```
重新登录 SSH 让权限生效。

### 安装 Docker Compose 插件
```bash
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -L https://github.com/docker/compose/releases/download/v2.24.6/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version
```

---

## 2. 拉取代码与启动服务
```bash
sudo mkdir -p /opt/logpulse-hr
sudo chown ubuntu:ubuntu /opt/logpulse-hr
cd /opt/logpulse-hr
git clone https://github.com/<ORG>/<REPO>.git .
docker compose up -d
```

---

## 3. 自签证书 + Basic Auth

### 生成自签证书（替换为公网 IP）
```bash
cd /opt/logpulse-hr
chmod +x scripts/gen-self-signed-cert.sh
./scripts/gen-self-signed-cert.sh <PUBLIC_IP>
```

### 创建 Basic Auth 账号
```bash
sudo apt install -y apache2-utils
sudo htpasswd -c /opt/logpulse-hr/nginx/.htpasswd admin
```

### 重启服务
```bash
docker compose up -d
```

---

## 4. Nginx 对外访问

### 访问地址
- Elasticsearch: `https://<PUBLIC_IP>/es/`
- Prometheus: `https://<PUBLIC_IP>/prom/`
- Prometheus 图形页：`https://<PUBLIC_IP>/graph`

浏览器会提示证书不受信任（自签证书），选择继续访问即可。

---

## 5. 验证服务状态

### 容器运行情况
```bash
docker compose ps
```

### Nginx 日志
```bash
docker compose logs --tail=50 nginx
```

### Prometheus 健康
```bash
curl -s http://127.0.0.1:9090/-/healthy
```

### Elasticsearch 健康
```bash
curl -s http://127.0.0.1:9200/_cluster/health
```

---

## 6. 验证数据是否产生

### Prometheus 指标
```bash
curl -s "http://127.0.0.1:9090/api/v1/query?query=logpulse_app_requests_total" | head -c 200
```

### Elasticsearch 日志
```bash
curl -k -u admin:<PASSWORD> "https://<PUBLIC_IP>/es/logpulse-logs/_search?size=1&sort=@timestamp:desc" | head -c 1000
```
---

## 7. GitHub Actions 自动部署触发

### 触发方式（空提交）
```bash
git commit --allow-empty -m "chore: trigger deploy"
git push
```

### 重新运行失败任务
GitHub → Actions → 选择 workflow → Re-run jobs

---

## 8. 调整实例规格（EC2 升级）

### 英文界面路径
1. EC2 Console → Instances  
2. Instance state → Stop instance  
3. Actions → Instance settings → Change instance type  
4. Apply → Start instance

---

## 9. 分配 Elastic IP

1. EC2 Console → Elastic IPs  
2. Allocate Elastic IP address  
3. Actions → Associate Elastic IP address  

---

## 10. 常见问题排查

### 443 无法访问
```bash
ss -lntp | grep :443

```

### ES 502（Nginx 无法访问上游）
```bash
docker exec -it logpulse-nginx sh -c "wget -qO- http://elasticsearch:9200 | head -c 200 || true"
```

### ES 进程退出（OOM）
```bash
docker compose logs --tail=50 elasticsearch
```
---

## 11. ES‑King 连接参数

- 连接地址：`https://<PUBLIC_IP>/es`
- 用户名：`admin`
- 密码：htpasswd 中设置的密码
- 使用 SSL：是
- 跳过 SSL：是（自签证书）
- CA 证书：可选（导入 `nginx/certs/server.crt`）
