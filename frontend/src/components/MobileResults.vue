<template>
  <div class="card-list">
    <div v-for="(stock, index) in stocks" :key="stock.code" class="stock-card">
      <div class="stock-card-header">
        <div class="stock-card-left">
          <span class="rank" :class="{ 'top-3': index < 3 }">{{ index + 1 }}</span>
          <div>
            <div class="stock-card-code">{{ stock.code }}</div>
            <div class="stock-card-name">{{ stock.name }}</div>
          </div>
        </div>
        <div style="text-align: right">
          <div class="stock-card-price">¥{{ stock.price?.toFixed(2) || '-' }}</div>
          <div class="stock-card-pct" :class="stock.pct_change >= 0 ? 'pct-up' : 'pct-down'">
            {{ formatPct(stock.pct_change) }}
          </div>
        </div>
      </div>
      <div class="stock-card-detail">
        <div class="stock-card-item">
          <div class="label">市盈率</div>
          <div class="val">{{ stock.pe ? stock.pe.toFixed(2) : '-' }}</div>
        </div>
        <div class="stock-card-item">
          <div class="label">市净率</div>
          <div class="val">{{ stock.pb ? stock.pb.toFixed(2) : '-' }}</div>
        </div>
        <div class="stock-card-item">
          <div class="label">市值(亿)</div>
          <div class="val">{{ formatMarketCap(stock.market_cap) }}</div>
        </div>
        <div class="stock-card-item">
          <div class="label">换手率</div>
          <div class="val">{{ stock.turnover_rate ? stock.turnover_rate.toFixed(2) + '%' : '-' }}</div>
        </div>
        <div class="stock-card-item">
          <div class="label">收益率</div>
          <div class="val">{{ formatPct(stock.pct_change) }}</div>
        </div>
        <div class="stock-card-item">
          <div class="label">流动性</div>
          <div class="val">{{ stock.turnover_rate ? stock.turnover_rate.toFixed(1) : '-' }}</div>
        </div>
        <div class="stock-card-item">
          <div class="label">技术分</div>
          <div class="val">{{ stock.tech_score }}</div>
        </div>
        <div class="stock-card-item">
          <div class="label">基本面</div>
          <div class="val">{{ stock.fund_score }}</div>
        </div>
        <div class="stock-card-item">
          <div class="label">综合分</div>
          <div class="val" style="color: #667eea">{{ stock.total_score }}</div>
        </div>
        <div class="stock-card-item">
          <div class="label">建议</div>
          <el-tag :type="getRecommendationType(stock.recommendation)" size="small">{{ stock.recommendation || '-' }}</el-tag>
        </div>
        <div v-if="stock.signals && stock.signals.length" class="stock-card-item signals-card-item">
          <div class="label">信号</div>
          <div class="signals-card">
            <el-tag 
              v-for="(sig, idx) in stock.signals.slice(0, 3)" 
              :key="idx" 
              :type="getSignalType(sig.type)" 
              size="small"
            >
              {{ sig.signal }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  stocks: {
    type: Array,
    default: () => []
  }
})

function formatPct(val) {
  if (!val && val !== 0) return '-'
  const sign = val > 0 ? '+' : ''
  return `${sign}${val.toFixed(2)}%`
}

function formatMarketCap(val) {
  if (!val || val === 0) return '-'
  return (val / 1e8).toFixed(1)
}

function getRecommendationType(rec) {
  if (rec === '强烈推荐') return 'success'
  if (rec === '推荐') return 'primary'
  if (rec === '中性') return 'info'
  if (rec === '观望') return 'warning'
  return 'danger'
}

function getSignalType(type) {
  if (type === 'bullish') return 'success'
  if (type === 'bearish') return 'danger'
  return 'info'
}
</script>

<style scoped>
.card-list {
  display: block;
}

.stock-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.stock-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.stock-card-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stock-card-code {
  font-size: 13px;
  color: #6c757d;
}

.stock-card-name {
  font-size: 16px;
  font-weight: 600;
}

.stock-card-price {
  font-size: 18px;
  font-weight: 700;
}

.stock-card-pct {
  font-size: 16px;
  font-weight: 600;
}

.stock-card-detail {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  font-size: 12px;
}

.stock-card-item {
  text-align: center;
}

.stock-card-item .label {
  color: #6c757d;
  margin-bottom: 2px;
}

.stock-card-item .val {
  font-weight: 600;
}

.signals-card {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: center;
}

.signals-card-item {
  flex-basis: 100%;
}

.rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 50%;
  font-weight: bold;
  font-size: 12px;
}

.rank.top-3 {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.pct-up {
  color: #dc3545;
}

.pct-down {
  color: #28a745;
}
</style>