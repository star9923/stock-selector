<template>
  <div class="app-container">
    <div v-if="pageLoading" class="page-loading">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>
    
    <div v-else class="page-content" :class="{ 'fade-in': !pageLoading }">
      <!-- 个股分析页面 -->
      <StockAnalysis v-if="currentView === 'analysis'" :init-code="stockCode" @back="currentView = 'selection'" />
      
      <!-- 选股页面 -->
      <div v-else>
        <div class="header">
          <p>技术面 + 基本面综合评分</p>
        </div>

        <div class="controls">
          <el-form :inline="true" :model="form" class="control-form">
            <el-form-item label="返回数量">
              <el-input-number v-model="form.top" :min="1" :max="100" />
            </el-form-item>
            <el-form-item label="最低得分">
              <el-input-number v-model="form.minScore" :min="0" :max="100" :step="5" />
            </el-form-item>
            <el-form-item label="技术面权重">
              <el-input-number v-model="form.techWeight" :min="0" :max="1" :step="0.1" :precision="1" />
            </el-form-item>
            <el-form-item label="基本面权重">
              <el-input-number v-model="form.fundWeight" :min="0" :max="1" :step="0.1" :precision="1" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleRun" :loading="loading">开始选股</el-button>
              <el-button type="danger" @click="handleStop" :disabled="!loading">停止选股</el-button>
              <el-button v-if="!isMobile" type="success" @click="currentView = 'analysis'">个股分析</el-button>
            </el-form-item>
          </el-form>
        </div>

      <el-alert v-if="message" :title="message" :type="messageType" show-icon :closable="false" class="alert" />

      <div v-if="loading" class="loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <p>正在分析 A 股市场，请稍候...</p>
      </div>

      <div v-else-if="stocks.length > 0" class="results">
        <div class="results-header">
          <h2>选股结果</h2>
          <span class="timestamp">更新时间: {{ timestamp }}</span>
        </div>

        <div class="summary">
          <div class="summary-card">
            <div class="label">选出股票</div>
            <div class="value">{{ stocks.length }} 只</div>
          </div>
          <div class="summary-card">
            <div class="label">平均涨幅</div>
            <div class="value">{{ avgChange }}%</div>
          </div>
          <div class="summary-card">
            <div class="label">最高涨幅</div>
            <div class="value">{{ maxChange }}%</div>
          </div>
          <div class="summary-card">
            <div class="label">平均综合分</div>
            <div class="value">{{ avgScore }}</div>
          </div>
        </div>

        <PcResults v-if="!isMobile" :stocks="stocks" @analyze="goToAnalysis" />
        <MobileResults v-else :stocks="stocks" />
      </div>

      <div v-else class="empty">
        <p>点击"开始选股"运行分析</p>
      </div>

      <div class="footer">
        <p>评分标准：根据估值、盈利能力、成长性、流动性，去掉 ST / *ST / 退市、涨停/跌停、价格 > 1 元、成交额 > 1000万；计分权重：技术分 0.6，基本面 0.4</p>
        <p>提示：智能选股仅供学习、参考，请勿用于实盘交易</p>
      </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { fetchStockData, runSelection, fetchFromJson, stopSelection, getStatus, getResult } from './api/index.js'
import PcResults from './components/PcResults.vue'
import MobileResults from './components/MobileResults.vue'
import StockAnalysis from './components/StockAnalysis.vue'

const currentView = ref('selection')
const stockCode = ref('')

const form = ref({
  top: 10,
  minScore: 40,
  techWeight: 0.8,
  fundWeight: 0.2
})

const loading = ref(false)
const pageLoading = ref(true)
const stocks = ref([])
const timestamp = ref('')
const message = ref('')
const messageType = ref('info')
const isMobile = ref(window.innerWidth <= 768)
let pollInterval = null

const avgChange = computed(() => {
  if (!stocks.value.length) return '0.00'
  const sum = stocks.value.reduce((acc, s) => acc + (s.pct_change || 0), 0)
  return (sum / stocks.value.length).toFixed(2)
})

const maxChange = computed(() => {
  if (!stocks.value.length) return '0.00'
  const max = Math.max(...stocks.value.map(s => s.pct_change || 0))
  return max.toFixed(2)
})

const avgScore = computed(() => {
  if (!stocks.value.length) return '0.0'
  const sum = stocks.value.reduce((acc, s) => acc + (s.total_score || 0), 0)
  return (sum / stocks.value.length).toFixed(1)
})

function handleResize() {
  isMobile.value = window.innerWidth <= 768
}

function goToAnalysis(code) {
  stockCode.value = code.replace('.SH', '').replace('.SZ', '')
  currentView.value = 'analysis'
}

async function loadData() {
  try {
    const result = await fetchFromJson()
    if (result.success) {
      stocks.value = result.data || []
      timestamp.value = result.timestamp || ''
      return
    }
    const result2 = await fetchStockData()
    if (result2.success) {
      stocks.value = result2.data || []
      timestamp.value = result2.timestamp || ''
    }
  } finally {
    pageLoading.value = false
  }
}

async function handleRun() {
  loading.value = true
  message.value = ''
  try {
    const res = await runSelection({
      top: form.value.top,
      min_score: form.value.minScore,
      tech_weight: form.value.techWeight,
      fund_weight: form.value.fundWeight
    })
    if (!res.success) {
      message.value = res.message || '选股失败'
      messageType.value = 'error'
      loading.value = false
      return
    }
    
    pollInterval = setInterval(async () => {
      const result = await getResult()
      if (result.done) {
        clearInterval(pollInterval)
        pollInterval = null
        loading.value = false
        if (result.success) {
          stocks.value = result.data || []
          timestamp.value = result.timestamp || ''
          message.value = `选股完成，共找到 ${result.count} 只股票`
          messageType.value = 'success'
        } else {
          message.value = result.message || '选股失败'
          messageType.value = 'error'
        }
      }
    }, 5000)
  } catch (e) {
    message.value = `请求失败: ${e.message}`
    messageType.value = 'error'
    loading.value = false
  }
}

async function handleStop() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
  try {
    const res = await stopSelection()
    message.value = res.message || '选股已停止'
    messageType.value = 'warning'
    loading.value = false
  } catch (e) {
    message.value = `停止失败: ${e.message}`
    messageType.value = 'error'
  }
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  padding: 20px;
}

.app-container {
  max-width: 1400px;
  margin: 0 auto;
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  overflow: hidden;
  position: relative;
  min-height: calc(100vh - 40px);
}

.page-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  z-index: 1000;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.page-loading p {
  margin-top: 16px;
  font-size: 16px;
}

.page-content.fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 30px;
  text-align: center;
}

.header p {
  opacity: 0.9;
  font-size: 14px;
}

.controls {
  padding: 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.control-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.control-form .el-form-item .el-button {
  margin-left: 8px;
}

.alert {
  margin: 20px;
}

.loading {
  text-align: center;
  padding: 60px;
  color: #6c757d;
}

.loading .el-icon {
  font-size: 40px;
  color: #667eea;
}

.results {
  padding: 20px;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.results-header h2 {
  color: #212529;
  font-size: 20px;
}

.timestamp {
  color: #6c757d;
  font-size: 14px;
}

.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 10px;
}

.summary-card {
  background: white;
  padding: 15px;
  border-radius: 10px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.summary-card .label {
  font-size: 12px;
  color: #6c757d;
  margin-bottom: 5px;
}

.summary-card .value {
  font-size: 20px;
  font-weight: 700;
  color: #667eea;
}

.empty {
  text-align: center;
  padding: 60px;
  color: #6c757d;
}

.footer {
  padding: 20px;
  background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
  color: #856404;
  font-size: 12px;
  text-align: center;
  border-top: 3px solid #ffc107;
}

.footer p {
  margin-bottom: 8px;
}

.footer p:last-child {
  color: #dc3545;
  font-weight: 600;
}

@media (max-width: 768px) {
  body {
    padding: 10px;
  }

  .header {
    padding: 20px;
  }

  .controls {
    display: none;
  }

  .control-form {
    flex-direction: column;
    align-items: stretch;
  }

  .control-form .el-form-item {
    margin-bottom: 10px;
  }

  .summary {
    grid-template-columns: repeat(2, 1fr);
    padding: 15px;
  }

  .results-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>