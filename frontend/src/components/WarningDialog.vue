<script setup lang="ts">
import { ref } from 'vue'

const visible = ref(false)

const open = () => {
  visible.value = true
}

defineExpose({ open })
</script>

<template>
  <el-dialog
    v-model="visible"
    title="⚠️ 重要警告"
    width="90%"
    :max-width="500"
    :close-on-click-modal="false"
    :show-close="false"
    :close-on-press-escape="false"
    class="warning-dialog"
  >
    <div class="warning-content">
      <el-alert
        title="内存操作风险"
        type="error"
        :closable="false"
        description="本工具通过直接操作游戏进程内存来实现功能。使用本工具存在以下风险："
      />

      <ul class="warning-list">
        <li>可能导致游戏崩溃或数据损坏</li>
        <li>可能导致存档损坏或丢失</li>
        <li>可能触发游戏不存在的反作弊机制</li>
      </ul>

      <el-alert
        title="使用前请确认"
        type="warning"
        :closable="false"
        class="confirm-section"
      >
        <ul class="confirm-list">
          <li>已备份重要存档</li>
          <li>了解并接受上述风险</li>
          <li>如有问题可尝试以管理员身份运行此工具</li>
        </ul>
      </el-alert>
    </div>

    <template #footer>
      <el-button type="danger" @click="visible = false">
        我已了解风险，继续使用
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.warning-content {
  padding: 8px 0;
}

.warning-list {
  margin: 16px 0;
  padding-left: 20px;
  color: var(--el-text-color-regular);
  line-height: 2;
}

.confirm-section {
  margin-top: 16px;
}

.confirm-list {
  margin: 8px 0 0 0;
  padding-left: 20px;
  color: var(--el-text-color-regular);
  line-height: 1.8;
}

:deep(.el-alert__description) {
  line-height: 1.6;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .warning-dialog {
    width: 90% !important;
    max-width: 400px;
  }

  .warning-list,
  .confirm-list {
    padding-left: 16px;
    font-size: 14px;
  }
}

@media (max-width: 480px) {
  .warning-dialog {
    width: 95% !important;
    max-width: 350px;
  }

  .warning-list,
  .confirm-list {
    padding-left: 12px;
    font-size: 13px;
    line-height: 1.6;
  }
}
</style>
