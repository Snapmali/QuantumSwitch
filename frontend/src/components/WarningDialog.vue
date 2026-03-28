<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const visible = ref(false)

const open = () => {
  visible.value = true
}

defineExpose({ open })
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="t('warningDialog.title')"
    width="500px"
    :close-on-click-modal="false"
    :show-close="false"
    :close-on-press-escape="false"
    class="warning-dialog"
  >
    <div class="warning-content">
      <el-alert
        :title="t('warningDialog.memoryRiskTitle')"
        type="error"
        :closable="false"
        :description="t('warningDialog.memoryRiskDescription')"
      />

      <ul class="warning-list">
        <li>{{ t('warningDialog.risk1') }}</li>
        <li>{{ t('warningDialog.risk2') }}</li>
        <li>{{ t('warningDialog.risk3') }}</li>
      </ul>

      <el-alert
        :title="t('warningDialog.confirmTitle')"
        type="warning"
        :closable="false"
        class="confirm-section"
      >
        <ul class="confirm-list">
          <li>{{ t('warningDialog.confirmItem1') }}</li>
          <li>{{ t('warningDialog.confirmItem2') }}</li>
          <li>{{ t('warningDialog.confirmItem3') }}</li>
        </ul>
      </el-alert>
    </div>

    <template #footer>
      <el-button type="danger" @click="visible = false">
        {{ t('warningDialog.acceptButton') }}
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
