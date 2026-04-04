<script setup lang="ts">
import { useTelegram } from '~/composables/useTelegram'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~/components/ui/tabs'

const { loading, error } = useTelegram()
</script>

<template>
  <div class="max-w-[900px] mx-auto">
    <h2 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase mb-4 flex items-center gap-2">
      <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
      Telegram Notifications
    </h2>

    <!-- Error -->
    <div v-if="error" class="text-[var(--bearish)] text-xs p-4 rounded-xl border border-[var(--border-sell)] mb-4">
      {{ error }}
    </div>

    <!-- Loading -->
    <template v-if="loading">
      <div class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-32 rounded-xl shimmer border border-[var(--surface-skeleton)]" />
      </div>
    </template>

    <template v-else>
      <Tabs default-value="templates">
        <TabsList class="mb-4">
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="rules">Rules</TabsTrigger>
          <TabsTrigger value="bot">Bot</TabsTrigger>
        </TabsList>

        <TabsContent value="templates">
          <TelegramTemplateEditor />
        </TabsContent>

        <TabsContent value="rules">
          <TelegramNotificationRules />
        </TabsContent>

        <TabsContent value="bot">
          <div class="space-y-4">
            <TelegramBotCommands />
            <TelegramChatManager />
          </div>
        </TabsContent>
      </Tabs>
    </template>
  </div>
</template>
