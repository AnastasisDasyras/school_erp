<script setup lang="ts">
// App shell only — no business logic here, that's the views' job.
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white border-b px-6 py-4">
      <h1 class="text-lg font-semibold text-gray-900">School ERP</h1>
    </header>
    <main class="p-6">
      <RouterView />
    </main>
  </div>
</template>
