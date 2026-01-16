<template>
    <div class="topbar">
        <div class="progress-bar" :style="{ width: `${displayProgress}%`, backgroundColor: displayProgressColor }" />
        <div class="tp heading">Scoreboard</div>
        <div class="tp countdown">{{ timeRemaining }}</div>
        <div class="tp round">Round: {{ displayRound }}{{ maxRound ? ` / ${maxRound}` : '' }}</div>
    </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useScoreboardStore } from '@/stores/scoreboard';

export default {
    setup() {
        const scoreboardStore = useScoreboardStore();
        const timer = ref(null);

        const round = computed(() => scoreboardStore.round);
        const maxRound = computed(() => scoreboardStore.maxRound);
        const roundProgress = computed(() => scoreboardStore.roundProgress);
        const roundTime = computed(() => scoreboardStore.roundTime);
        const roundStart = computed(() => scoreboardStore.roundStart);

        const isGameEnded = computed(() => {
            return maxRound.value && round.value > maxRound.value;
        });

        const displayRound = computed(() => {
            return isGameEnded.value ? maxRound.value : round.value;
        });

        const displayProgress = computed(() => {
            return isGameEnded.value ? 0 : roundProgress.value;
        });

        const progressBarColor = computed(() => {
            if (roundProgress.value < 60) {
                return '#B9FBC0';
            }
            if (roundProgress.value < 85) {
                return '#FDFFB6';
            }
            return '#FFADAD';
        });

        const displayProgressColor = computed(() => {
            if (isGameEnded.value) {
                return 'transparent';
            }
            return progressBarColor.value;
        });

        const timeRemaining = computed(() => {
            if (isGameEnded.value) {
                return 'Game Ended!!!';
            }

            if (roundTime.value === null || roundStart.value === null || round.value < 1) {
                return '00:00';
            }

            // Trigger reactivity on roundProgress change
            const _ = roundProgress.value;
            const currentTime = new Date().getTime() / 1000;
            const roundEndTime = roundStart.value + roundTime.value;
            const remainingSeconds = Math.max(0, Math.floor(roundEndTime - currentTime));
            
            const minutes = Math.floor(remainingSeconds / 60);
            const seconds = remainingSeconds % 60;
            
            return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        });

        onMounted(async () => {
            await scoreboardStore.fetchRoundTime();
            timer.value = setInterval(
                () => scoreboardStore.calculateRoundProgress(),
                500
            );
        });

        onBeforeUnmount(() => {
            if (timer.value) {
                clearInterval(timer.value);
            }
        });

        return {
            displayRound,
            maxRound,
            displayProgress,
            displayProgressColor,
            timeRemaining,
        };
    },
};
</script>

<style lang="scss" scoped>
.tp {
    font-size: 1.1em;
    font-weight: bold;
    z-index: 1;
}

.heading {
    font-size: 1.3em;
}

.countdown {
    font-size: 1.5em;
}

.topbar {
    position: relative;
    background: #bbbbbb55;
    padding: 1em 3em;

    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 2em;
}

.heading {
    justify-self: start;
}

.countdown {
    justify-self: center;
}

.round {
    justify-self: end;
}

.progress-bar {
    height: 100%;
    position: absolute;
    top: 0;
    left: 0;
}
</style>