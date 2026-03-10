<template>
  <router-view />
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  /* Prevent font scaling on iOS */
  -webkit-text-size-adjust: 100%;
  /* Smooth scrolling */
  scroll-behavior: smooth;
}

body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  /* Prevent pull-to-refresh on mobile */
  overscroll-behavior: none;
}

#app {
  width: 100%;
  height: 100vh;
  /* Ensure proper viewport height on mobile browsers */
  height: 100dvh;
}

/* Global mobile optimizations */
@media (max-width: 768px) {
  /* Larger touch targets */
  .el-button {
    min-height: 40px;
    min-width: 40px;
  }

  /* Improve touch feedback */
  .el-button:active {
    transform: scale(0.98);
  }

  /* Larger form inputs */
  .el-input__inner {
    min-height: 40px;
  }

  /* Better spacing for cards */
  .el-card {
    border-radius: 12px;
  }

  /* Larger pagination buttons */
  .el-pagination .el-pager li {
    min-width: 36px;
    height: 36px;
    line-height: 36px;
  }

  .el-pagination button {
    min-width: 36px;
    height: 36px;
    line-height: 36px;
  }

  /* Ensure text wraps on mobile */
  * {
    word-wrap: break-word;
  }
}

/* Small mobile optimizations */
@media (max-width: 480px) {
  .el-button {
    min-height: 36px;
    min-width: 36px;
  }

  .el-input__inner {
    min-height: 36px;
  }

  .el-card {
    border-radius: 8px;
  }

  .el-pagination .el-pager li {
    min-width: 32px;
    height: 32px;
    line-height: 32px;
    font-size: 12px;
  }

  .el-pagination button {
    min-width: 32px;
    height: 32px;
    line-height: 32px;
  }

  /* Prevent horizontal overflow */
  body {
    overflow-x: hidden;
  }

  /* Ensure all containers respect viewport width */
  .el-card, .el-dialog {
    max-width: 100vw;
    box-sizing: border-box;
  }

  /* Dialog responsive */
  .el-dialog {
    width: 90% !important;
    margin: 10vh auto !important;
  }

  /* Ensure text wraps properly */
  * {
    word-wrap: break-word;
    overflow-wrap: break-word;
  }
}
</style>
