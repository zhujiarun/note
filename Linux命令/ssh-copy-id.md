# ssh-copy-id 免密登录

## 命令

```bash
ssh-copy-id root@192.168.12.20
```

如果要指定端口：

```bash
ssh-copy-id -p 10024 cloubox_07@192.168.17.110
```
## 说明

将本地 SSH 公钥（默认 `~/.ssh/id_rsa.pub`）分发到远程服务器 `192.168.12.200` 的 root 用户，之后即可免密 SSH 登录。

执行时需要输入远程服务器的 root 密码。

## 适用场景

- protocol_adapter 项目 ansible 部署时，需要通过 SSH 连接到 `192.168.12.200`（protocol_run 组）
- ansible playbook 使用 `remote_user: root`，需要免密登录
