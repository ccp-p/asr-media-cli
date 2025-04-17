# === 前端构建阶段 ===
FROM node:18-alpine AS build

# 安装 pnpm
RUN npm install -g pnpm

# 设置工作目录
WORKDIR /app

# 拷贝前端源码
COPY ./BillNote_frontend /app

# 安装依赖并构建
RUN pnpm install && pnpm run build

# === nginx 运行阶段 ===
FROM nginx:alpine

# 拷贝模板配置
COPY ./BillNote_frontend/deploy/default.conf.template /etc/nginx/templates/default.conf.template

# 拷贝构建产物
COPY --from=build /app/dist /usr/share/nginx/html

# 拷贝启动脚本
COPY ./BillNote_frontend/deploy/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 80

# 使用启动脚本启动容器
CMD ["/start.sh"]