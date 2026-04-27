<template>
  <div class="stock-analysis">
    <div class="analysis-header">
      <el-button @click="goBack" :icon="ArrowLeft" circle />
      <h2>个股深度分析</h2>
    </div>

    <div class="search-bar">
      <el-input
        v-model="stockCode"
        placeholder="请输入股票代码 (如: 000001)"
        @keyup.enter="handleAnalyze"
        style="width: 200px"
      />
      <el-button type="primary" @click="handleAnalyze" :loading="loading">分析</el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="alert" />

    <div v-if="loading" class="loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <p>正在深度分析...</p>
    </div>

    <div v-else-if="result && result.success" class="analysis-content">
      <!-- 操作建议 - 顶部突出显示 -->
      <div class="advice-banner" :class="getAdviceClass(result.operation_advice.action)">
        <div class="advice-grid">
          <div class="advice-col main">
            <span class="action">{{ result.operation_advice.action }}</span>
            <!-- <span class="reason">{{ result.operation_advice.reason }}</span> -->
          </div>
          <div class="advice-col detail">
            <div class="detail-row">
              <span class="label">📈 技术面:</span>
              <span class="value">{{ result.operation_advice.tech_reason }}</span>
            </div>
            <div class="detail-row">
              <span class="label">📊 基本面:</span>
              <span class="value">{{ result.operation_advice.fund_reason }}</span>
            </div>
            <div class="detail-row">
              <span class="label">💰 资金面:</span>
              <span class="value">{{ result.operation_advice.flow_advice }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 核心指标区域 - 紧凑两栏布局 -->
      <div class="core-grid">
        <!-- 基本信息 -->
        <div class="card">
          <div class="card-title">📊 基本信息</div>
          <div class="card-content">
            <div class="stat">
              <span class="label">代码</span>
              <span class="value">{{ result.code }}</span>
            </div>
            <div class="stat">
              <span class="label">名称</span>
              <span class="value">{{ result.name }}</span>
            </div>
            <div class="stat">
              <span class="label">价格</span>
              <span class="value price">¥{{ result.basic_info.price?.toFixed(2) }}</span>
            </div>
            <div class="stat">
              <span class="label">涨跌</span>
              <span :class="['value', result.basic_info.pct_change >= 0 ? 'up' : 'down']">
                {{ formatPct(result.basic_info.pct_change) }}
              </span>
            </div>
          </div>
        </div>

        <!-- 技术面 -->
        <div class="card">
          <div class="card-title">📈 技术面 <el-tag :type="getScoreTag(result.technical.score.total)" size="small">{{ result.technical.score.total }}分</el-tag></div>
          <div class="card-content">
            <div class="stat">
              <span class="label">MA5/10/20</span>
              <span class="value">{{ result.technical.ma5?.toFixed(1) }}/{{ result.technical.ma10?.toFixed(1) }}/{{ result.technical.ma20?.toFixed(1) }}</span>
            </div>
            <div class="stat">
              <span class="label">MA60</span>
              <span class="value">{{ result.technical.ma60?.toFixed(1) }}</span>
            </div>
            <div class="stat">
              <span class="label">MACD(DIF)</span>
              <span class="value">{{ result.technical.macd_dif?.toFixed(2) }}</span>
            </div>
            <div class="stat">
              <span class="label">MACD(DEA)</span>
              <span class="value">{{ result.technical.macd_dea?.toFixed(2) }}</span>
            </div>
            <div class="stat">
              <span class="label">RSI(14)</span>
              <span :class="['value', getRsiClass(result.technical.rsi)]">{{ result.technical.rsi?.toFixed(1) }}</span>
            </div>
            <div class="stat">
              <span class="label">KDJ</span>
              <span class="value">K:{{ result.technical.kdj_k?.toFixed(1) }} D:{{ result.technical.kdj_d?.toFixed(1) }} J:{{ result.technical.kdj_j?.toFixed(1) }}</span>
            </div>
            <div class="stat">
              <span class="label">布林带</span>
              <span class="value">{{ result.technical.boll_lower?.toFixed(1) }}/{{ result.technical.boll_mid?.toFixed(1) }}/{{ result.technical.boll_upper?.toFixed(1) }}</span>
            </div>
          </div>
        </div>

        <!-- 基本面 -->
        <div class="card">
          <div class="card-title">📋 基本面 <el-tag :type="getScoreTag(result.fundamental.score.total)" size="small">{{ result.fundamental.score.total }}分</el-tag></div>
          <div class="card-content">
            <div class="stat">
              <span class="label">市盈率(PE)</span>
              <span :class="['value', getPeClass(result.fundamental.pe)]">{{ result.fundamental.pe?.toFixed(2) }}</span>
            </div>
            <div class="stat">
              <span class="label">市净率(PB)</span>
              <span :class="['value', getPbClass(result.fundamental.pb)]">{{ result.fundamental.pb?.toFixed(2) }}</span>
            </div>
            <div class="stat">
              <span class="label">ROE</span>
              <span class="value">{{ result.fundamental.roe?.toFixed(2) }}%</span>
            </div>
            <div class="stat">
              <span class="label">资产负债率</span>
              <span class="value">{{ result.fundamental.debt_ratio?.toFixed(1) }}%</span>
            </div>
            <div class="stat">
              <span class="label">换手率</span>
              <span class="value">{{ result.fundamental.turnover_rate?.toFixed(2) }}%</span>
            </div>
            <div class="stat">
              <span class="label">市值(亿)</span>
              <span class="value">{{ formatMarketCap(result.fundamental.market_cap) }}</span>
            </div>
          </div>
        </div>

        <!-- 资金流向 -->
        <div class="card">
          <div class="card-title">💰 资金流向 <span class="sub">(近{{ result.fund_flow.days || 5 }}日)</span></div>
          <div class="card-content">
            <div class="stat">
              <span class="label">主力</span>
              <span :class="['value', getFlowClass(result.fund_flow.main_net)]">{{ formatMoney(result.fund_flow.main_net) }}</span>
            </div>
            <div class="stat">
              <span class="label">超大单</span>
              <span :class="['value', getFlowClass(result.fund_flow.super_net)]">{{ formatMoney(result.fund_flow.super_net) }}</span>
            </div>
            <div class="stat">
              <span class="label">大单</span>
              <span :class="['value', getFlowClass(result.fund_flow.large_net)]">{{ formatMoney(result.fund_flow.large_net) }}</span>
            </div>
            <div class="stat">
              <span class="label">综合分</span>
              <span class="value total-score">{{ calculateTotalScore() }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 趋势预测 -->
      <div class="trend-bar">
        <span class="trend-label">🔮 趋势预测:</span>
        <el-tag :type="getTrendTag(result.trend.short)" class="trend-tag">短期(1-3天) {{ result.trend.short }}</el-tag>
        <el-tag :type="getTrendTag(result.trend.mid)" class="trend-tag">中期(4-10天) {{ result.trend.mid }}</el-tag>
        <el-tag :type="getTrendTag(result.trend.long)" class="trend-tag">长期(11-20天) {{ result.trend.long }}</el-tag>
      </div>

      <!-- 交易信号 -->
      <div class="signals-bar">
        <span class="signals-label">⚡ 交易信号:</span>
        <el-tag
          v-for="(sig, idx) in result.signals"
          :key="idx"
          :type="getSignalType(sig.type)"
          size="small"
        >
          {{ sig.signal }}
        </el-tag>
        <span v-if="!result.signals?.length" class="no-signal">暂无信号</span>
      </div>

      <!-- 综合建议 -->
      <div class="signals-bar">
        <span class="signals-label">🎯 综合建议:</span>
        <el-tag :type="getRecommendationTag(result.recommendation)" size="large">{{ result.recommendation }}</el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ArrowLeft, Loading } from '@element-plus/icons-vue'
import { analyzeStock as apiAnalyzeStock } from '../api/index.js'

const props = defineProps({
  initCode: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['back'])

const stockCode = ref('')
const loading = ref(false)
const result = ref(null)
const error = ref('')

onMounted(() => {
  if (props.initCode) {
    stockCode.value = props.initCode
    handleAnalyze()
  }
})

async function handleAnalyze() {
  if (!stockCode.value) {
    error.value = '请输入股票代码'
    return
  }
  loading.value = true
  error.value = ''
  result.value = null
  try {
    const res = await apiAnalyzeStock(stockCode.value)
    console.log('[StockAnalysis] response:', res)
    if (res.success) {
      result.value = res
    } else {
      error.value = res.error || '分析失败'
    }
  } catch (e) {
    error.value = `请求失败: ${e.message}`
  } finally {
    loading.value = false
  }
}

function goBack() {
  emit('back')
}

function formatPct(val) {
  if (!val && val !== 0) return '-'
  const sign = val > 0 ? '+' : ''
  return `${sign}${val.toFixed(2)}%`
}

function formatMoney(val) {
  if (!val) return '-'
  const absVal = Math.abs(val)
  if (absVal >= 100000000) return `${(val / 100000000).toFixed(2)}亿`
  if (absVal >= 10000) return `${(val / 10000).toFixed(2)}万`
  return `${val.toFixed(0)}`
}

function formatMarketCap(val) {
  if (!val || val === 0) return '-'
  return (val / 1e8).toFixed(1)
}

function calculateTotalScore() {
  if (!result.value || result.value.total_score === undefined) return '-'
  return result.value.total_score
}

function getPeClass(pe) {
  if (!pe || pe <= 0) return ''
  if (pe < 15) return 'pe-low'
  if (pe < 30) return 'pe-mid'
  return 'pe-high'
}

function getPbClass(pb) {
  if (!pb || pb <= 0) return ''
  if (pb < 1) return 'pb-low'
  if (pb < 3) return 'pb-mid'
  return 'pb-high'
}

function getScoreTag(score) {
  if (score >= 70) return 'success'
  if (score >= 50) return 'warning'
  return 'danger'
}

function getRsiClass(rsi) {
  if (rsi < 30) return 'rsi-oversold'
  if (rsi > 70) return 'rsi-overbought'
  return ''
}

function getFlowClass(val) {
  if (!val) return ''
  return val > 0 ? 'flow-up' : 'flow-down'
}

function getTrendTag(trend) {
  if (trend === '看涨') return 'danger'
  if (trend === '看跌') return 'success'
  return 'info'
}

function getSignalType(type) {
  if (type === 'bullish') return 'success'
  if (type === 'bearish') return 'danger'
  return 'info'
}

function getAdviceClass(action) {
  if (action === '强烈买入') return 'advice-strong-buy'
  if (action === '买入') return 'advice-buy'
  if (action === '持有') return 'advice-hold'
  if (action === '减仓') return 'advice-reduce'
  return 'advice-sell'
}

function getRecommendationTag(rec) {
  if (rec === '强烈推荐') return 'success'
  if (rec === '推荐') return 'primary'
  if (rec === '观望') return 'warning'
  return 'danger'
}
</script>

<style scoped>
.stock-analysis {
  padding: 15px;
}

.analysis-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
}

.analysis-header h2 {
  color: #333;
  margin: 0;
  font-size: 18px;
}

.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.alert {
  margin-bottom: 15px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #6c757d;
}

.loading .el-icon {
  font-size: 32px;
  color: #667eea;
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.advice-banner {
  padding: 15px 20px;
  border-radius: 10px;
  color: white;
}

.advice-strong-buy { background: linear-gradient(135deg, #67c23a, #85ce61); }
.advice-buy { background: linear-gradient(135deg, #409eff, #66b1ff); }
.advice-hold { background: linear-gradient(135deg, #909399, #a6a9ad); }
.advice-reduce { background: linear-gradient(135deg, #e6a23c, #ebb563); }
.advice-sell { background: linear-gradient(135deg, #f56c6c, #f78989); }

.advice-grid {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 20px;
}

.advice-col.main {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.advice-col.main .action {
  font-size: 22px;
  font-weight: 700;
}

.advice-col.main .reason {
  font-size: 12px;
  opacity: 0.9;
  margin-top: 4px;
}

.advice-col.detail {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
}

.detail-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.detail-row .label {
  font-weight: 500;
  min-width: 70px;
}

.detail-row .value {
  opacity: 0.95;
}

.core-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.stat .label {
  color: #999;
}

.stat .value {
  color: #333;
  font-weight: 500;
}

.stat .value.price { color: #667eea; }
.stat .value.up { color: #dc3545; }
.stat .value.down { color: #28a745; }
.stat .value.rsi-oversold { color: #28a745; }
.stat .value.rsi-overbought { color: #dc3545; }
.stat .value.flow-up { color: #dc3545; }
.stat .value.flow-down { color: #28a745; }

.stat .value.pe-low { color: #28a745; }
.stat .value.pe-mid { color: #e6a23c; }
.stat .value.pe-high { color: #dc3545; }
.stat .value.pb-low { color: #28a745; }
.stat .value.pb-mid { color: #e6a23c; }
.stat .value.pb-high { color: #dc3545; }

.stat .value.total-score { color: #667eea; font-weight: 700; }

.trend-bar, .signals-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 12px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.trend-label, .signals-label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.trend-tag { margin-right: 8px; }

.no-signal {
  color: #999;
  font-size: 12px;
}

.final-result {
  text-align: center;
  padding: 15px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

@media (max-width: 1200px) {
  .core-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 768px) {
  .core-grid { grid-template-columns: 1fr; }
  .advice-detail { flex-direction: column; gap: 5px; }
}
</style>