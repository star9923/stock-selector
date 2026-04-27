<template>
  <div class="pc-results">
    <el-table :data="stocks" stripe class="stock-table" :cell-class-name="getCellClass">
      <el-table-column prop="index" label="排名" min-width="70">
        <template #default="{ $index }">
          <span class="rank" :class="{ 'top-3': $index < 3 }">{{ $index + 1 }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="code" label="代码" min-width="120" />
      <el-table-column prop="name" label="名称" min-width="100" />
      <el-table-column label="价格" min-width="80">
        <template #default="{ row }">
          ¥{{ row.price?.toFixed(2) || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="涨跌幅" min-width="80">
        <template #default="{ row }">
          <span :class="row.pct_change >= 0 ? 'pct-up' : 'pct-down'">
            {{ formatPct(row.pct_change) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="投资建议" min-width="100">
        <template #default="{ row }">
          <el-tag :type="getRecommendationType(row.recommendation)">{{ row.recommendation || '-' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="交易信号" min-width="120">
        <template #default="{ row }">
          <div v-if="row.signals && row.signals.length" class="signals-cell">
            <span v-for="(sig, idx) in row.signals.slice(0, 3)" :key="idx" >
              <el-tooltip effect="dark" placement="top" trigger="hover" :content="sig.desc"> 
                <el-tag 
                  :type="getSignalType(sig.type)" 
                  size="small" 
                  class="signal-tag"
                >
                  {{ sig.signal }}
                </el-tag>
              </el-tooltip>
            </span>
          </div>
          <span v-else>-</span>
        </template>
      </el-table-column>
      
      <el-table-column label="换手率" min-width="80">
        <template #default="{ row }">
          {{ row.turnover_rate && row.turnover_rate > 0 ? row.turnover_rate.toFixed(2) + '%' : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="技术分" min-width="80">
        <template #default="{ row }">
          <el-tag :type="getScoreType(row.tech_score)">{{ row.tech_score }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="基本分" min-width="80">
        <template #default="{ row }">
          <el-tag :type="getScoreType(row.fund_score)">{{ row.fund_score }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="综合分" min-width="80">
        <template #default="{ row }">
          <el-tag type="primary">{{ row.total_score }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="pe" label="市盈率" min-width="80">
        <template #default="{ row }">
          {{ row.pe && row.pe > 0 ? row.pe.toFixed(2) : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="pb" label="市净率" min-width="80">
        <template #default="{ row }">
          {{ row.pb && row.pb > 0 ? row.pb.toFixed(2) : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="市值(亿)" min-width="80">
        <template #default="{ row }">
          {{ row.market_cap && row.market_cap > 0 ? formatMarketCap(row.market_cap) : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="100" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="$emit('analyze', row.code)">深度分析</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
defineProps({
  stocks: {
    type: Array,
    default: () => []
  }
})

defineEmits(['analyze'])

function formatPct(val) {
  if (!val && val !== 0) return '-'
  const sign = val > 0 ? '+' : ''
  return `${sign}${val.toFixed(2)}%`
}

function formatMarketCap(val) {
  if (!val || val === 0) return '-'
  return (val / 1e8).toFixed(1)
}

function getScoreType(score) {
  if (score >= 70) return 'success'
  if (score >= 50) return 'warning'
  return 'danger'
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

function getCellClass({ columnIndex }) {
  if (columnIndex === 4) return 'pct-cell'
  return ''
}
</script>

<style scoped>
.pc-results {
  width: 100%;
}

.stock-table {
  min-width: 100%;
}

.stock-table .pct-cell {
  font-weight: 600;
}

.signals-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.signal-tag {
  margin: 2px;
}

.pct-up {
  color: #dc3545;
}

.pct-down {
  color: #28a745;
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
</style>