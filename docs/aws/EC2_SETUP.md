# AWS EC2 开通步骤（适用于部署 LogPulse HR）

本指南以免费额度为前提，使用 Amazon Linux 2 或 Ubuntu 作为示例。  
目标：开通 EC2、配置安全组、完成基础登录与环境准备。

## 1. 创建密钥对
1. 登录 AWS 控制台 → EC2 → “密钥对”。
2. 点击“创建密钥对”，类型选 RSA。
3. 下载生成的 `.pem` 文件并妥善保管（后续 SSH 登录使用）。

## 2. 创建安全组
1. EC2 → “安全组” → “创建安全组”。
2. 入站规则建议：
   - SSH（22）：仅允许你的公网 IP
   - HTTP（80）：0.0.0.0/0（如果需要公开访问）
   - HTTPS（443）：0.0.0.0/0（如果需要 TLS）
3. 出站规则保持默认（允许全部）。

## 3. 启动实例
1. EC2 → “实例” → “启动实例”。
2. 选择 AMI：
   - Amazon Linux 2 或 Ubuntu 22.04 LTS
3. 实例类型：
   - 免费额度：t2.micro / t3.micro
4. 选择密钥对（第 1 步创建的 PEM）。
5. 选择安全组（第 2 步创建的安全组）。
6. 存储默认即可（8~30GB）。
7. 点击“启动实例”。

## 4. 分配与绑定公网地址（可选但推荐）
1. EC2 → “弹性 IP” → “分配弹性 IP 地址”。
2. “关联弹性 IP 地址”到刚创建的实例。
3. 这样实例重启后公网 IP 不会变化。

## 5. SSH 登录实例
1. 修改 PEM 文件权限：
   ```bash
   chmod 400 /path/to/your-key.pem
   ```
2. 登录（Amazon Linux 默认用户 `ec2-user`，Ubuntu 默认用户 `ubuntu`）：
   ```bash
   ssh -i /path/to/your-key.pem ec2-user@<EC2_PUBLIC_IP>
   ```

## 6. 基础环境准备（用于部署容器）
### Amazon Linux 2
```bash
sudo yum update -y
sudo yum install -y docker git
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ec2-user
```

### Ubuntu 22.04
```bash
sudo apt update -y
sudo apt install -y docker.io git
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

> 重新登录 SSH 后 Docker 权限生效。

## 7. 安装 Docker Compose 插件
```bash
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -L https://github.com/docker/compose/releases/download/v2.24.6/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version
```

## 8. 预留部署目录
```bash
sudo mkdir -p /opt/logpulse-hr
sudo chown $USER:$USER /opt/logpulse-hr
```

## 9. 常见问题排查
- SSH 连接超时：检查安全组是否放通 22，并确认公网 IP 正确。
- 无法用 Docker：确认已重新登录 SSH，或执行 `groups` 查看是否在 docker 组。
- 公网访问不了：检查安全组 80/443 是否放通。

---

完成以上步骤后，你可以继续配置 GitHub Actions 自动部署与回写部署状态。
