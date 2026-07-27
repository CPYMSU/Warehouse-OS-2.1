# Warehouse Member 微信小程序

面向多公司的统一消费者／经营者微信小程序。微信消费者身份仍与 Warehouse 员工身份隔离，
但同一个微信登录可以按服务端授权自动进入消费者端或经营端。没有 Warehouse 公司的经营者也能
注册独立经营空间，并使用会员、钱包、充值、消费、排班和预约功能。

## 本地预览

1. 在微信开发者工具中导入本目录 `wechat-miniapp/`。
2. 确认 `project.config.json` 使用正式小程序 AppID；不要把上传私钥或 AppSecret 放进项目。
3. 在 `miniprogram/config/env.js` 配置测试 API 地址与默认公司代码。
4. 后端环境配置：

   - `WECHAT_MINIAPP_APP_ID`
   - `WECHAT_MINIAPP_APP_SECRET`
   - `MEMBER_IDENTITY_MASTER_KEY`（至少 32 字节）
   - `MEMBER_FINANCE_OUTBOX_ENABLED=1`
   - `MEMBER_FINANCE_OUTBOX_INTERVAL_SECONDS=30`

   微信支付 API v3 密钥、商户私钥、平台公钥/证书与绑定激活步骤见
   `../docs/WECHAT_MEMBER_PLATFORM.md`。

AppSecret、API v3 密钥、商户私钥和上传私钥不得出现在本目录或前端代码中。

## 上传微信开发版本

正式 AppID 已配置在 `project.config.json`。在 GitHub 仓库中只需配置一次 Actions
Secret `WECHAT_MINIPROGRAM_PRIVATE_KEY`，其值为微信公众平台生成的上传私钥全文；
不要把 `.key` 文件、私钥内容或本机私钥路径提交到 Git。

随后从 GitHub Actions 手动运行 `Upload WeChat Mini Program`，填写版本号与说明。
工作流会使用锁定依赖执行 `npm ci` 和前端契约测试，再将 Secret 临时写入
runner 的临时目录并调用 `npm run upload`。无论上传成功或失败，临时私钥都会删除。
该操作只上传微信开发版本；体验版、审核与正式发布仍需在微信公众平台按对应流程完成。

## 浏览器 H5 体验台

原生 WXML/WXSS 和 `wx.login` 不能直接由普通浏览器执行。开发阶段可访问部署后的
`https://bonfirework.org/member-preview.html`，使用 Swiss 风格 H5 体验台检查公司切换、
演示充值、付款码、流水、等级与抽奖交互。该页面只使用浏览器本地演示数据；读取公司时
也只调用公开公司预览接口，不会发起真实支付或改写会员资金。

## 前端契约测试

在本目录运行 `npm test`。测试不依赖第三方包，会检查直达页面的登录/公司守卫、
公司二维码 `scene` 与热启动邀请、公开公司与正式同意条款、金额及本地时间格式、
充值/抽奖幂等键持久化、跨公司临时状态清理，以及服务端会话撤销先于本地清理等
关键约束。

## 当前边界

- 同一小程序已包含消费者端和经营端；登录后由 `app-context` 自动返回可用入口，也允许同时具有两种身份的用户手动切换。
- 独立经营者不需要 Warehouse 公司即可注册和配置工作室、服务、工作人员、公司时区、
  营业时间及每位工作人员自己的空闲时间。
- Warehouse 公司代码会被配置成隔离的 APP 公司空间；首次可信绑定后，只同步有效公司管理权限，不保存 Warehouse 密码或临时 token。
- Warehouse 联动公司的所有 APP 业务事件会通过可靠 outbox 幂等写入 Warehouse 档案；充值、消费及销售型礼品卡另生成财务草稿，等待财务主管补充科目并确认，不会自动过账。
- 微信登录、注册、公司会员空间、余额、流水、双边充值／扣费卡片、Swiss 二维码、礼品卡、预约与爽约规则均已接入后端接口。
- 默认充值不调用 `wx.requestPayment`，也不要求经营者开通微信支付商户 API。消费者发起充值卡片后，由经营者确认已经在线下或双方认可的渠道收款，服务端才记入余额；消费者随后确认收到。每一步都保存为独立、幂等且不可变的业务事件。
- 扣费由经营者建立扣费卡片或扫描消费者的一次性 Swiss 付款码，消费者确认后才扣除余额；销售型和赠送型礼品卡均由服务端签发，领取时原子核销，不能重复使用。
- 小程序发布与 Vultr 后端部署相互独立：代码先由微信开发者工具上传体验版，正式版仍需微信审核。
- “Warehouse 2.0 已绑定”表示可信身份与公司管理权限已建立映射；APP 原始业务账本仍保存在各公司独立数据库，Warehouse 接收不可变事件档案和待审核财务草稿，不宣称与所有 Warehouse 模块实时双向同步。
