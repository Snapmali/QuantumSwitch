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
}
</style>
