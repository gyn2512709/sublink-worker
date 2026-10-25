# 自动更新

每天北京时间 04:43，由 GitHub Actions 检查 `7Sageer/sublink-worker` 的 `main` 分支。
存在新提交时同步源码，运行上游测试、现有短链接兼容测试和部署构建检查。全部成功后才更新本仓库 `main`；Cloudflare Builds 再次检查并部署 `sublink-worker`。

`.github/`、`.deployment/`、`personal/` 和根目录 Wrangler 配置不被上游覆盖。部署必须使用 `.deployment/wrangler.jsonc`，固定复用线上 `SUBLINK_KV`，不运行自动创建 KV 的 `npm run deploy`。

域名 `sub.397256.xyz`、直连规则、洛杉矶订阅、访问密钥及小时刷新属于独立的 `sublink-personal` 服务。本流水线不部署该服务，不更换任何现有订阅链接。

每周仅更新一次 `sync-state.json` 以保持公开仓库活跃；Cloudflare 构建忽略该文件。同步或测试失败时不提交更新，当前线上版本继续服务。GitHub Actions 会记录失败；可在 Actions 中手动运行本工作流重试。

升级失败时在 Cloudflare 中回滚 `sublink-worker` 的部署版本；不要删除或新建 KV。首次启用前版本：`b5e61a8e-6cdf-4524-be4d-473604fb317c`。
