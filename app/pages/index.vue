<template>
  <div class="space-y-5 md:space-y-6">
    <!-- Row 1: Active Signals (left) | Market Pulse + Strategy Performance stacked (right) -->
    <div class="grid grid-cols-1 md:grid-cols-11 gap-5">
      <div class="md:col-span-6 anim-in anim-delay-1">
        <ActiveSignals />
      </div>
      <div class="md:col-span-5 space-y-5">
        <div class="anim-in anim-delay-2">
          <MarketPulse />
        </div>
        <div class="anim-in anim-delay-3">
          <StrategyPerformance />
        </div>
      </div>
    </div>

    <!-- Row 2: Heatmap (full width) -->
    <div class="anim-in anim-delay-4">
      <Heatmap />
    </div>

    <!-- Row 3: Currency Strength (full width) -->
    <div class="anim-in anim-delay-5">
      <CurrencyStrength />
    </div>
  </div>
</template>
