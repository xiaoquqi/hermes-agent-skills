---
name: github-install-skill-offline
description: 当终端无法直接 clone GitHub 仓库时，通过 GitHub API tarball 接口绕过网络限制安装技能
---

# GitHub 仓库离线安装（终端网络不通时）

## 问题
- `git clone git@github.com:xxx` 或 `git clone https://github.com/xxx` 超时
- 系统配置了代理（如 Clash Verge），但 `curl --proxy http://127.0.0.1:7890` TLS handshake 卡住
- 浏览器能访问 GitHub，但下载文件触发浏览器行为，无法保存到目标路径

## 解决：GitHub API tarball 下载

```bash
# 1. 用 curl 下载 tarball（GitHub API 不走代理但 curl 可达）
curl -s --max-time 30 -L \
  -H "Accept: application/vnd.github.v3+json" \
  -H "User-Agent: Mozilla/5.0" \
  "https://api.github.com/repos/{owner}/{repo}/tarball/{branch}" \
  -o /tmp/repo.tar.gz

# 2. 解压
tar -xzf /tmp/repo.tar.gz -C /tmp/

# 3. 移动到 skills 目录
ls /tmp/ | grep {repo}  # 找解压出的目录名
mv /tmp/{owner}-{repo}-{commit}/ ~/.hermes/skills/{category}/{repo-name}/

# 4. 推送 git
cd ~/.hermes/skills
git add {category}/{repo-name}/
git commit -m "Add {repo-name} from github.com/{owner}/{repo}"
git push
```

## 关键点
- GitHub API (`api.github.com`) 可能比 `raw.githubusercontent.com` 更容易连通
- `-L` 跟随重定向，`--max-time 30` 防卡死
- 解压目录名格式：`{owner}-{repo}-{commit}`，需先 `ls /tmp/` 确认
- 跳过 PNG 验证文件（`scripts/verify-output/`）可大幅减少下载量
- 225 文件的仓库 tarball 约 9MB，30s 内可完成

## 验证代理实际端口（Clash Verge）
```bash
# Clash Verge 可能监听在随机端口，不是默认的 7890
lsof -nP -iTCP -sTCP:LISTEN | grep -i clash
# 常见：33331 等随机高端口
```
