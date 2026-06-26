# DuerOS Smart Home (小度智能家居) - Home Assistant 集成

将 Home Assistant 设备暴露给百度 DuerOS（小度智能音箱），实现语音控制。

## 功能特性

### 支持的设备类型

| HA 设备类型 | DuerOS 设备类型 | 支持的操作 |
|------------|----------------|-----------|
| `light` (灯) | LIGHT | 开/关、亮度、颜色、色温 |
| `switch` (开关) | SWITCH | 开/关 |
| `input_boolean` | SWITCH | 开/关 |
| `fan` (风扇) | FAN | 开/关、风速调节 |
| `cover` (窗帘) | CURTAIN | 开/关/停、位置控制 |
| `climate` (空调) | AIR_CONDITION | 开/关、温度、模式、风速 |
| `humidifier` (加湿器) | HUMIDIFIER | 开/关、湿度 |
| `scene` (场景) | SCENE_TRIGGER | 触发 |
| `automation` | SCENE_TRIGGER | 触发 |
| `sensor` (传感器) | SENSOR | 查询温度/湿度 |

### 语音命令示例

- "小度小度，打开客厅灯"
- "小度小度，把卧室灯调到50%"
- "小度小度，把灯调成蓝色"
- "小度小度，空调调到26度"
- "小度小度，打开窗帘"
- "小度小度，客厅温度多少"

---

## 安装步骤

### 1. 安装组件

将 `custom_components/dueros_smarthome` 文件夹复制到你 HA 的 `custom_components/` 目录下。

```
<config>/
└── custom_components/
    └── dueros_smarthome/
        ├── __init__.py
        ├── api.py
        ├── config_flow.py
        ├── const.py
        ├── http_api.py
        ├── manifest.json
        ├── mapping.py
        ├── oauth2.py
        ├── strings.json
        ├── translations/
        │   └── zh-Hans.json
        └── README.md
```

### 2. 重启 Home Assistant

### 3. 添加集成

在 HA 中：**设置 → 设备与服务 → 添加集成 → 搜索 "DuerOS Smart Home"**

输入你在 DuerOS 开放平台创建的 **Client ID** 和 **Client Secret**。

### 4. DuerOS 开放平台配置

#### 4.1 创建智能家居技能

1. 打开 [DuerOS 开放平台](https://dueros.baidu.com/dbp/bot/index#/iotopenplatform)
2. 登录百度账号
3. 点击 **云云控制台 → 创建技能**
4. 选择 **智能家居** 类型

#### 4.2 配置 OAuth2

在技能配置页面：

| 配置项 | 值 |
|--------|-----|
| 授权方式 | OAuth2 |
| Client ID | 你在 HA 中配置的值 |
| Client Secret | 你在 HA 中配置的值 |
| Authorization URL | `https://你的HA域名/auth/dueros/authorize` |
| Token URL | `https://你的HA域名/auth/dueros/token` |

#### 4.3 配置设备云接口

| 配置项 | 值 |
|--------|-----|
| 接口地址 | `https://你的HA域名/api/dueros/smarthome` |

#### 4.4 测试 & 发布

1. 在 DuerOS 控制台点击 **测试**
2. 用小度 APP 扫码授权
3. 说 "小度小度，发现设备"
4. 测试通过后点击 **发布**

---

## 网络要求

### 前提条件

你的 Home Assistant **必须能被公网 HTTPS 访问**。

### 方案一：Nginx 反向代理 + Let's Encrypt

```nginx
server {
    listen 443 ssl http2;
    server_name ha.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/ha.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ha.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8123;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 方案二：Cloudflare Tunnel

```bash
# 安装 cloudflared
cloudflared tunnel create ha-tunnel
cloudflared tunnel route dns ha-tunnel ha.yourdomain.com

# 配置文件 ~/.cloudflared/config.yml
tunnel: <tunnel-id>
credentials-file: ~/.cloudflared/<tunnel-id>.json
ingress:
  - hostname: ha.yourdomain.com
    service: http://localhost:8123
  - service: http_status:404
```

### 方案三：FRP / ngrok / Tailscale Funnel

任何能提供公网 HTTPS 到内网 HA 转发的方案都行。

---

## 故障排除

### 授权失败

- 确认 HA 能通过公网 HTTPS 访问
- 确认 Authorization URL 和 Token URL 可以从外网访问
- 检查 Client ID / Secret 是否一致
- 查看 HA 日志：`logger: debug` for `custom_components.dueros_smarthome`

### 设备发现为空

- 确认 HA 中有可控设备（light, switch, cover 等）
- 设备状态不能是 `unavailable`
- 在 HA 开发者工具中测试 `POST /api/dueros/smarthome` 是否有响应

### 语音控制无反应

- 在 DuerOS 控制台重新测试接口
- 确认设备名称没有冲突
- 检查 token 是否过期

---

## 日志调试

在 `configuration.yaml` 中添加：

```yaml
logger:
  default: info
  logs:
    custom_components.dueros_smarthome: debug
```

---

## 技术架构

```
┌─────────────┐    HTTPS    ┌─────────────────┐    HA API    ┌──────────┐
│  DuerOS 平台  │ ─────────→ │  Home Assistant  │ ─────────→ │  设备/实体  │
│  (小度音箱)   │ ←───────── │  (本组件)        │ ←───────── │          │
└─────────────┘   JSON响应   └─────────────────┘   状态查询   └──────────┘
```

1. DuerOS 发送 HTTPS 请求到 HA 的 `/api/dueros/smarthome`
2. 本组件解析 DuerOS ConnectedHome 协议
3. 将请求转换为 HA 服务调用
4. 返回 DuerOS 格式的 JSON 响应

---

## License

Apache-2.0

交流学习：QQ295358024
