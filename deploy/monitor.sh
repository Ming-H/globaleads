#!/bin/bash
# ============================================================
# GlobalLeads 服务器监控脚本
# 部署方式：crontab 每 5 分钟执行一次
#   */5 * * * * /home/admin/globaleads/deploy/monitor.sh >> /home/admin/globaleads/logs/monitor.log 2>&1
# ============================================================

set -euo pipefail

# ==================== 配置 ====================

# 项目根目录（服务器上的路径）
PROJECT_DIR="${PROJECT_DIR:-/home/admin/globaleads}"
LOG_DIR="${PROJECT_DIR}/logs"

# 告警阈值
MEMORY_WARN_PERCENT=85      # 内存使用率警告阈值
MEMORY_CRIT_PERCENT=92      # 内存使用率紧急阈值
DISK_WARN_PERCENT=85        # 磁盘使用率警告阈值
DISK_CRIT_PERCENT=95        # 磁盘使用率紧急阈值
CONTAINER_MEM_WARN_PERCENT=80  # 容器内存使用率警告阈值（占 limit 百分比）

# 飞书 Webhook（通过环境变量或 .env 文件配置）
FEISHU_WEBHOOK_URL="${FEISHU_WEBHOOK_URL:-}"

# 加载 .env 文件（如果存在）
ENV_FILE="${PROJECT_DIR}/deploy/.env"
if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    FEISHU_WEBHOOK_URL="${FEISHU_WEBHOOK_URL:-}"
fi

# ==================== 工具函数 ====================

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

log_info() {
    echo "$(timestamp) [INFO] $*"
}

log_warn() {
    echo "$(timestamp) [WARN] $*"
}

log_error() {
    echo "$(timestamp) [ERROR] $*"
}

# 发送飞书告警
send_feishu_alert() {
    local level="$1"
    local title="$2"
    local content="$3"

    if [[ -z "$FEISHU_WEBHOOK_URL" ]]; then
        log_warn "飞书 Webhook 未配置，跳过发送 | title=$title"
        return
    fi

    local color="blue"
    if [[ "$level" == "WARN" ]]; then
        color="orange"
    elif [[ "$level" == "CRIT" ]]; then
        color="red"
    fi

    local payload
    payload=$(cat <<EOF
{
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "[$level] GlobalLeads $title"
            },
            "template": "$color"
        },
        "elements": [
            {
                "tag": "markdown",
                "content": "$content"
            }
        ]
    }
}
EOF
)

    # 发送请求，超时 10 秒，失败不中断脚本
    curl -s -m 10 -X POST "$FEISHU_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "$payload" > /dev/null 2>&1 || true
}

# ==================== 检查项 ====================

ALERT_COUNT=0

# 1. 检查整体内存使用率
check_memory() {
    log_info "--- 检查内存使用率 ---"

    local mem_info
    mem_info=$(free -m | grep "Mem:")
    local total used percent
    total=$(echo "$mem_info" | awk '{print $2}')
    used=$(echo "$mem_info" | awk '{print $3}')
    percent=$((used * 100 / total))

    log_info "内存 | total=${total}MB used=${used}MB percent=${percent}%"

    if [[ $percent -ge $MEMORY_CRIT_PERCENT ]]; then
        log_error "内存紧急! 使用率 ${percent}% >= ${MEMORY_CRIT_PERCENT}%"
        send_feishu_alert "CRIT" "内存紧急" "服务器内存使用率 **${percent}%**，已超过紧急阈值 ${MEMORY_CRIT_PERCENT}%\n已用 ${used}MB / 总计 ${total}MB\n请立即处理！"
        ALERT_COUNT=$((ALERT_COUNT + 1))
    elif [[ $percent -ge $MEMORY_WARN_PERCENT ]]; then
        log_warn "内存警告 | 使用率 ${percent}% >= ${MEMORY_WARN_PERCENT}%"
        send_feishu_alert "WARN" "内存警告" "服务器内存使用率 **${percent}%**，已超过警告阈值 ${MEMORY_WARN_PERCENT}%\n已用 ${used}MB / 总计 ${total}MB"
        ALERT_COUNT=$((ALERT_COUNT + 1))
    fi
}

# 2. 检查磁盘使用率
check_disk() {
    log_info "--- 检查磁盘使用率 ---"

    local disk_info
    disk_info=$(df -h / | tail -1)
    local percent_str
    percent_str=$(echo "$disk_info" | awk '{print $5}' | tr -d '%')
    local avail
    avail=$(echo "$disk_info" | awk '{print $4}')

    log_info "磁盘 | used_percent=${percent_str}% avail=${avail}"

    if [[ $percent_str -ge $DISK_CRIT_PERCENT ]]; then
        log_error "磁盘紧急! 使用率 ${percent_str}% >= ${DISK_CRIT_PERCENT}%"
        send_feishu_alert "CRIT" "磁盘紧急" "根磁盘使用率 **${percent_str}%**，已超过紧急阈值 ${DISK_CRIT_PERCENT}%\n剩余可用 ${avail}"
        ALERT_COUNT=$((ALERT_COUNT + 1))
    elif [[ $percent_str -ge $DISK_WARN_PERCENT ]]; then
        log_warn "磁盘警告 | 使用率 ${percent_str}% >= ${DISK_WARN_PERCENT}%"
        send_feishu_alert "WARN" "磁盘警告" "根磁盘使用率 **${percent_str}%**，已超过警告阈值 ${DISK_WARN_PERCENT}%\n剩余可用 ${avail}"
        ALERT_COUNT=$((ALERT_COUNT + 1))
    fi
}

# 3. 检查容器状态和内存
check_containers() {
    log_info "--- 检查容器状态 ---"

    local containers=("globaleads-backend" "globaleads-celery")

    # LeadMine 容器也一起监控（如果存在）
    local leadmine_containers=("leadmine-backend" "leadmine-celery-worker")
    for c in "${leadmine_containers[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${c}$"; then
            containers+=("$c")
        fi
    done

    for container in "${containers[@]}"; do
        # 检查容器是否在运行
        if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            log_error "容器已停止 | container=$container"
            send_feishu_alert "CRIT" "容器停止" "容器 **${container}** 已停止运行!\n请立即检查并重启。"
            ALERT_COUNT=$((ALERT_COUNT + 1))
            continue
        fi

        # 检查健康状态
        local health
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
        if [[ "$health" == "unhealthy" ]]; then
            log_error "容器不健康 | container=$container health=$health"
            send_feishu_alert "WARN" "容器不健康" "容器 **${container}** 健康检查失败\n状态: $health"
            ALERT_COUNT=$((ALERT_COUNT + 1))
        else
            log_info "容器健康 | container=$container health=$health"
        fi

        # 检查容器内存使用（如果有 mem_limit）
        local mem_usage mem_limit
        mem_usage=$(docker stats --no-stream --format '{{.MemUsage}}' "$container" 2>/dev/null || echo "N/A")
        log_info "容器内存 | container=$container usage=$mem_usage"

        # 解析 mem_limit 检查是否接近上限
        local limit_bytes
        limit_bytes=$(docker inspect --format='{{.HostConfig.Memory}}' "$container" 2>/dev/null || echo "0")
        if [[ "$limit_bytes" -gt 0 ]]; then
            local usage_bytes
            usage_bytes=$(docker inspect --format='{{.MemoryStats.Usage}}' "$container" 2>/dev/null || echo "0")
            if [[ "$usage_bytes" -gt 0 ]]; then
                local usage_percent=$((usage_bytes * 100 / limit_bytes))
                if [[ $usage_percent -ge $CONTAINER_MEM_WARN_PERCENT ]]; then
                    log_warn "容器内存接近上限 | container=$container percent=${usage_percent}%"
                    send_feishu_alert "WARN" "容器内存高" "容器 **${container}** 内存使用率 **${usage_percent}%**\n接近限制上限 ${CONTAINER_MEM_WARN_PERCENT}%"
                    ALERT_COUNT=$((ALERT_COUNT + 1))
                fi
            fi
        fi
    done
}

# 4. 检查 PostgreSQL 连通性
check_postgres() {
    log_info "--- 检查 PostgreSQL ---"

    # 尝试通过 LeadMine 的 postgres 容器连接
    local pg_container
    pg_container=$(docker ps --format '{{.Names}}' | grep postgres | head -1)

    if [[ -z "$pg_container" ]]; then
        log_warn "未找到 PostgreSQL 容器"
        return
    fi

    local result
    result=$(docker exec "$pg_container" pg_isready -U leadmine 2>&1) || true

    if echo "$result" | grep -q "accepting connections"; then
        log_info "PostgreSQL 正常 | container=$pg_container"
    else
        log_error "PostgreSQL 连接失败 | container=$pg_container result=$result"
        send_feishu_alert "CRIT" "数据库异常" "PostgreSQL 连接失败!\n容器: $pg_container\n错误: $result"
        ALERT_COUNT=$((ALERT_COUNT + 1))
    fi
}

# 5. 检查 Redis 连通性
check_redis() {
    log_info "--- 检查 Redis ---"

    local redis_container
    redis_container=$(docker ps --format '{{.Names}}' | grep redis | head -1)

    if [[ -z "$redis_container" ]]; then
        log_warn "未找到 Redis 容器"
        return
    fi

    local result
    result=$(docker exec "$redis_container" redis-cli ping 2>&1) || true

    if echo "$result" | grep -q "PONG"; then
        log_info "Redis 正常 | container=$redis_container"
    else
        log_error "Redis 连接失败 | container=$redis_container result=$result"
        send_feishu_alert "CRIT" "Redis 异常" "Redis 连接失败!\n容器: $redis_container\n错误: $result"
        ALERT_COUNT=$((ALERT_COUNT + 1))
    fi
}

# ==================== 主流程 ====================

main() {
    mkdir -p "$LOG_DIR"

    log_info "========== 开始监控检查 =========="

    check_memory
    check_disk
    check_containers
    check_postgres
    check_redis

    log_info "========== 检查完成 | alerts=$ALERT_COUNT =========="

    # 清理超过 7 天的监控日志
    if command -v find &> /dev/null; then
        find "$LOG_DIR" -name "monitor.log" -mtime +7 -delete 2>/dev/null || true
    fi
}

main "$@"
